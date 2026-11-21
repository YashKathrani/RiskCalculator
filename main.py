import ctypes
import json
import math
import os
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import customtkinter as ctk

# ---------------------------------------------------------------------------
# Colors / theme
# ---------------------------------------------------------------------------
BG = "#151515"
CARD_BG = "#1f1f1f"
PILL_BG = "#2a2a2a"
FIELD_BG = "#262626"
FIELD_BORDER = "#3a3a3a"
LIME = "#D7FF3F"
LIME_HOVER = "#C3EA2C"
TEXT_MAIN = "#F2F2F2"
TEXT_SUB = "#8C8C8C"
TEXT_SUB2 = "#6E6E6E"
DANGER = "#FF6B6B"
GREEN = "#3ED07A"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

SETTINGS_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "PositionSizer"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# symbol -> (name, tick size, tick value $, point value $)
CONTRACTS = {
    "MNQ": ("Micro Nasdaq-100", 0.25, 0.50, 2.00),
    "MES": ("Micro S&P 500", 0.25, 1.25, 5.00),
    "MYM": ("Micro Dow", 1.0, 0.50, 0.50),
    "M2K": ("Micro Russell 2000", 0.10, 0.50, 5.00),
    "NQ": ("Nasdaq-100", 0.25, 5.00, 20.00),
    "ES": ("S&P 500", 0.25, 12.50, 50.00),
    "YM": ("Dow", 1.0, 5.00, 5.00),
    "RTY": ("Russell 2000", 0.10, 5.00, 50.00),
    "MGC": ("Micro Gold", 0.10, 1.00, 10.00),
    "MCL": ("Micro Crude Oil", 0.01, 1.00, 100.00),
}

DEFAULTS = {
    "contract": "MNQ",
    "account_balance": "50000",
    "risk_type": "Dollar",
    "risk_value": "",
    "stop_type": "Points",
    "stop_value": "",
    "rr_ratio": "",
}


def fmt_num(v):
    if float(v) == int(v):
        return f"{int(v)}"
    return f"{v:.4f}".rstrip("0").rstrip(".")


def fmt_money(v):
    return f"${v:,.2f}"


class Pill(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=PILL_BG, corner_radius=8, **kwargs)
        self.label_key = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=9), text_color=TEXT_SUB)
        self.label_val = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_MAIN
        )
        self.label_key.pack(pady=(6, 0))
        self.label_val.pack(pady=(0, 6))

    def set(self, key, val):
        self.label_key.configure(text=key)
        self.label_val.configure(text=val)


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title, **kwargs):
        super().__init__(master, fg_color=CARD_BG, corner_radius=10, **kwargs)
        self.title_lbl = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=9, weight="bold"), text_color=TEXT_SUB, anchor="w"
        )
        self.value_lbl = ctk.CTkLabel(
            self, text="--", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_MAIN, anchor="w"
        )
        self.sub_lbl = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=10), text_color=TEXT_SUB2, anchor="w"
        )
        self.title_lbl.pack(fill="x", padx=12, pady=(10, 2))
        self.value_lbl.pack(fill="x", padx=12, pady=0)
        self.sub_lbl.pack(fill="x", padx=12, pady=(0, 10))

    def set(self, value, sub=""):
        self.value_lbl.configure(text=value)
        self.sub_lbl.configure(text=sub)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Position Sizer")
        self.geometry("360x560")
        self.minsize(320, 380)
        self.configure(fg_color=BG)

        self.contract_var = ctk.StringVar(value=DEFAULTS["contract"])
        self.balance_var = ctk.StringVar(value=DEFAULTS["account_balance"])
        self.risk_type_var = ctk.StringVar(value=DEFAULTS["risk_type"])
        self.risk_value_var = ctk.StringVar(value=DEFAULTS["risk_value"])
        self.stop_type_var = ctk.StringVar(value=DEFAULTS["stop_type"])
        self.stop_value_var = ctk.StringVar(value=DEFAULTS["stop_value"])
        self.rr_var = ctk.StringVar(value=DEFAULTS["rr_ratio"])

        self._build_ui()
        self._load_settings()
        self._on_contract_change(self.contract_var.get())

        # auto-calculate if we restored usable numbers
        if self.risk_value_var.get() and self.stop_value_var.get():
            self.calculate()

    # ------------------------------------------------------------------
    def _entry(self, master, var, placeholder=None, fh=28):
        return ctk.CTkEntry(
            master,
            textvariable=var,
            placeholder_text=placeholder,
            fg_color=FIELD_BG,
            border_color=FIELD_BORDER,
            border_width=1,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=11),
            corner_radius=8,
            height=fh,
        )

    def _segmented(self, master, values, var, command, fh=28):
        seg = ctk.CTkSegmentedButton(
            master,
            values=values,
            variable=var,
            command=command,
            fg_color=PILL_BG,
            selected_color=LIME,
            selected_hover_color=LIME_HOVER,
            unselected_color=PILL_BG,
            unselected_hover_color="#333333",
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=11),
            corner_radius=8,
            height=fh,
        )
        try:
            seg.configure(selected_text_color="#101010", unselected_text_color=TEXT_MAIN)
        except Exception:
            pass
        return seg

    def _build_ui(self):
        pad = 14
        gap = 6
        fh = 28

        header = ctk.CTkLabel(
            self,
            text="Position Sizer",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT_MAIN,
            anchor="w",
        )
        header.pack(fill="x", padx=pad, pady=(12, 2))
        underline = ctk.CTkFrame(self, fg_color=LIME, height=2, width=70, corner_radius=1)
        underline.pack(anchor="w", padx=pad, pady=(0, 10))

        body = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=PILL_BG,
            scrollbar_button_hover_color="#3a3a3a",
        )
        body.pack(fill="both", expand=True, padx=pad - 4, pady=0)
        body._parent_canvas.configure(yscrollincrement=22)  # snappier scrolling
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        row = 0
        # Contract + Account balance
        self._label(body, "CONTRACT").grid(row=row, column=0, sticky="w", pady=(0, 3))
        self._label(body, "ACCOUNT BALANCE ($)").grid(row=row, column=1, sticky="w", pady=(0, 3), padx=(10, 0))
        row += 1

        contract_values = [self._contract_display(sym) for sym in CONTRACTS]
        self.contract_menu = ctk.CTkOptionMenu(
            body,
            values=contract_values,
            command=self._on_contract_select,
            fg_color=FIELD_BG,
            button_color=PILL_BG,
            button_hover_color="#333333",
            dropdown_fg_color=FIELD_BG,
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=11),
            dropdown_font=ctk.CTkFont(size=11),
            corner_radius=8,
            height=fh,
        )
        self.contract_menu.set(self._contract_display(self.contract_var.get()))
        self.contract_menu.grid(row=row, column=0, sticky="ew", pady=(0, gap))

        self.balance_entry = self._entry(body, self.balance_var)
        self.balance_entry.grid(row=row, column=1, sticky="ew", pady=(0, gap), padx=(10, 0))
        row += 1

        # Pills
        pills_frame = ctk.CTkFrame(body, fg_color="transparent")
        pills_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        pills_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.pill_tick = Pill(pills_frame)
        self.pill_tick.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.pill_tickval = Pill(pills_frame)
        self.pill_tickval.grid(row=0, column=1, sticky="ew", padx=4)
        self.pill_pointval = Pill(pills_frame)
        self.pill_pointval.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        row += 1

        # Risk type + risk value
        self._label(body, "RISK TYPE").grid(row=row, column=0, sticky="w", pady=(0, 3))
        self.risk_value_label = self._label(body, "RISK PER TRADE ($)")
        self.risk_value_label.grid(row=row, column=1, sticky="w", pady=(0, 3), padx=(10, 0))
        row += 1

        self.risk_type_seg = self._segmented(
            body, ["Percent", "Dollar"], self.risk_type_var, self._on_risk_type_change
        )
        self.risk_type_seg.grid(row=row, column=0, sticky="ew", pady=(0, gap))
        self.risk_value_entry = self._entry(body, self.risk_value_var, "e.g. 50")
        self.risk_value_entry.grid(row=row, column=1, sticky="ew", pady=(0, gap), padx=(10, 0))
        row += 1

        # Stop distance
        self._label(body, "STOP DISTANCE").grid(row=row, column=0, sticky="w", pady=(0, 3))
        self.stop_value_label = self._label(body, "STOP DISTANCE (POINTS)")
        self.stop_value_label.grid(row=row, column=1, sticky="w", pady=(0, 3), padx=(10, 0))
        row += 1

        self.stop_type_seg = self._segmented(
            body, ["Points", "Ticks"], self.stop_type_var, self._on_stop_type_change
        )
        self.stop_type_seg.grid(row=row, column=0, sticky="ew", pady=(0, gap))
        self.stop_value_entry = self._entry(body, self.stop_value_var, "e.g. 25")
        self.stop_value_entry.grid(row=row, column=1, sticky="ew", pady=(0, gap), padx=(10, 0))
        row += 1

        # R:R ratio (optional, full width)
        rr_label_row = ctk.CTkFrame(body, fg_color="transparent")
        rr_label_row.grid(row=row, column=0, columnspan=2, sticky="ew")
        self._label(rr_label_row, "R:R RATIO").pack(side="left")
        ctk.CTkLabel(
            rr_label_row,
            text="OPTIONAL",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=TEXT_SUB2,
            fg_color=PILL_BG,
            corner_radius=5,
        ).pack(side="left", padx=(6, 0), ipadx=5, ipady=1)
        row += 1

        self.rr_entry = self._entry(body, self.rr_var, "e.g. 2")
        self.rr_entry.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(3, 3))
        row += 1

        ctk.CTkLabel(
            body,
            text="Calculates profit target in dollars",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_SUB2,
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 12))
        row += 1

        # Calculate button
        ctk.CTkButton(
            body,
            text="Calculate position size",
            command=self.calculate,
            fg_color=LIME,
            hover_color=LIME_HOVER,
            text_color="#101010",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            height=36,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        row += 1

        ctk.CTkFrame(body, fg_color=FIELD_BORDER, height=1).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(0, 12)
        )
        row += 1

        # Results cards
        cards_frame = ctk.CTkFrame(body, fg_color="transparent")
        cards_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        cards_frame.grid_columnconfigure((0, 1), weight=1)
        self.card_contracts = StatCard(cards_frame, "CONTRACTS")
        self.card_contracts.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 8))
        self.card_dollar_risk = StatCard(cards_frame, "DOLLAR RISK")
        self.card_dollar_risk.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 8))
        self.card_risk_per = StatCard(cards_frame, "RISK PER CONTRACT")
        self.card_risk_per.grid(row=1, column=0, columnspan=2, sticky="nsew")
        row += 1

        self.profit_card = StatCard(body, "PROFIT TARGET")  # gridded on demand
        self.profit_row = row
        row += 1

        # Risk % of account bar
        pct_card = ctk.CTkFrame(body, fg_color=CARD_BG, corner_radius=10)
        pct_card.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(8, 12))
        top_row = ctk.CTkFrame(pct_card, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(
            top_row, text="RISK AS % OF ACCOUNT", font=ctk.CTkFont(size=10, weight="bold"),
            text_color=TEXT_SUB,
        ).pack(side="left")
        self.pct_value_lbl = ctk.CTkLabel(
            top_row, text="0.00%", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MAIN
        )
        self.pct_value_lbl.pack(side="right")
        self.risk_bar = ctk.CTkProgressBar(
            pct_card, progress_color=GREEN, fg_color=PILL_BG, height=7, corner_radius=4
        )
        self.risk_bar.set(0)
        self.risk_bar.pack(fill="x", padx=12, pady=(0, 12))
        row += 1

        self.status_lbl = ctk.CTkLabel(
            body, text="", font=ctk.CTkFont(size=10), text_color=DANGER,
            anchor="w", wraplength=300, justify="left",
        )
        self.status_lbl.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 6))
        row += 1

        # Save button
        self.save_btn = ctk.CTkButton(
            body,
            text="Save Settings",
            command=self.save_settings,
            fg_color=PILL_BG,
            hover_color="#333333",
            text_color=TEXT_MAIN,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=8,
            height=32,
        )
        self.save_btn.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 16))

    def _label(self, master, text):
        return ctk.CTkLabel(
            master, text=text, font=ctk.CTkFont(size=10, weight="bold"), text_color=TEXT_SUB, anchor="w"
        )

    def _contract_display(self, sym):
        return f"{sym} — {CONTRACTS[sym][0]}"

    # ------------------------------------------------------------------
    def _on_contract_select(self, display_value):
        sym = display_value.split(" — ")[0]
        self.contract_var.set(sym)
        self._on_contract_change(sym)

    def _on_contract_change(self, sym):
        if sym not in CONTRACTS:
            sym = "MNQ"
        _, tick, tick_val, point_val = CONTRACTS[sym]
        self.pill_tick.set("Tick", fmt_num(tick))
        self.pill_tickval.set("Tick value", fmt_money(tick_val))
        self.pill_pointval.set("Point value", fmt_money(point_val))

    def _on_risk_type_change(self, value):
        self.risk_value_label.configure(
            text="RISK PER TRADE (%)" if value == "Percent" else "RISK PER TRADE ($)"
        )

    def _on_stop_type_change(self, value):
        self.stop_value_label.configure(
            text="STOP DISTANCE (TICKS)" if value == "Ticks" else "STOP DISTANCE (POINTS)"
        )

    # ------------------------------------------------------------------
    def calculate(self):
        self.status_lbl.configure(text="")
        try:
            sym = self.contract_var.get()
            if sym not in CONTRACTS:
                sym = "MNQ"
            _, tick, tick_val, point_val = CONTRACTS[sym]

            balance = float(self.balance_var.get().replace(",", ""))
            risk_raw = float(self.risk_value_var.get().replace(",", ""))
            stop_raw = float(self.stop_value_var.get().replace(",", ""))

            if balance <= 0:
                raise ValueError("Account balance must be greater than 0.")
            if risk_raw <= 0:
                raise ValueError("Risk per trade must be greater than 0.")
            if stop_raw <= 0:
                raise ValueError("Stop distance must be greater than 0.")

            if self.risk_type_var.get() == "Percent":
                if risk_raw > 100:
                    raise ValueError("Risk percent must be 100 or less.")
                dollar_risk = balance * (risk_raw / 100.0)
            else:
                dollar_risk = risk_raw

            if self.stop_type_var.get() == "Ticks":
                stop_ticks = stop_raw
                stop_points = stop_raw * tick
            else:
                stop_points = stop_raw
                stop_ticks = stop_raw / tick

            risk_per_contract = stop_points * point_val
            if risk_per_contract <= 0:
                raise ValueError("Stop distance produced an invalid risk per contract.")

            contracts_raw = dollar_risk / risk_per_contract
            # small epsilon so e.g. 0.9999999 from float error still rounds to 1
            contracts = math.floor(contracts_raw + 1e-9)
            per_contract_sub = f"{fmt_num(stop_ticks)} ticks · {fmt_num(stop_points)} pts"

            if contracts < 1:
                self.card_contracts.set("0", f"Rounded down from {contracts_raw:.2f}")
                self.card_dollar_risk.set(fmt_money(0), "0.00% of account")
                self.card_risk_per.set(fmt_money(risk_per_contract), per_contract_sub)
                self.pct_value_lbl.configure(text="0.00%")
                self.risk_bar.set(0)
                self._hide_profit_card()
                self.status_lbl.configure(
                    text="Risk budget is smaller than the risk of one contract at this stop distance.",
                    text_color=DANGER,
                )
                return

            actual_dollar_risk = contracts * risk_per_contract
            risk_pct_of_account = (actual_dollar_risk / balance) * 100

            self.card_contracts.set(str(contracts), f"Rounded down from {contracts_raw:.2f}")
            self.card_dollar_risk.set(fmt_money(actual_dollar_risk), f"{risk_pct_of_account:.2f}% of account")
            self.card_risk_per.set(fmt_money(risk_per_contract), per_contract_sub)

            self.pct_value_lbl.configure(text=f"{risk_pct_of_account:.2f}%")
            self.risk_bar.set(min(risk_pct_of_account / 5.0, 1.0))

            rr_text = self.rr_var.get().strip()
            if rr_text:
                rr = float(rr_text)
                if rr <= 0:
                    raise ValueError("R:R ratio must be greater than 0.")
                self.profit_card.set(fmt_money(actual_dollar_risk * rr), f"{rr:g}:1 reward:risk")
                self.profit_card.grid(row=self.profit_row, column=0, columnspan=2, sticky="ew", pady=(0, 14))
            else:
                self._hide_profit_card()

        except ValueError as e:
            msg = str(e)
            if msg.startswith("could not convert"):
                msg = "Enter valid numbers in all required fields."
            self.status_lbl.configure(text=msg or "Enter valid numbers in all required fields.", text_color=DANGER)
        except Exception:
            self.status_lbl.configure(text="Enter valid numbers in all required fields.", text_color=DANGER)

    def _hide_profit_card(self):
        self.profit_card.grid_forget()

    # ------------------------------------------------------------------
    def _load_settings(self):
        data = dict(DEFAULTS)
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    data.update({k: str(v) for k, v in saved.items() if k in DEFAULTS})
        except Exception:
            pass

        if data["contract"] not in CONTRACTS:
            data["contract"] = "MNQ"
        if data["risk_type"] not in ("Percent", "Dollar"):
            data["risk_type"] = "Dollar"
        if data["stop_type"] not in ("Points", "Ticks"):
            data["stop_type"] = "Points"

        self.contract_var.set(data["contract"])
        self.contract_menu.set(self._contract_display(data["contract"]))
        self.balance_var.set(data["account_balance"])
        self.risk_type_var.set(data["risk_type"])
        self.risk_value_var.set(data["risk_value"])
        self.stop_type_var.set(data["stop_type"])
        self.stop_value_var.set(data["stop_value"])
        self.rr_var.set(data["rr_ratio"])

        self._on_risk_type_change(data["risk_type"])
        self._on_stop_type_change(data["stop_type"])

    def save_settings(self):
        data = {
            "contract": self.contract_var.get(),
            "account_balance": self.balance_var.get().strip(),
            "risk_type": self.risk_type_var.get(),
            "risk_value": self.risk_value_var.get().strip(),
            "stop_type": self.stop_type_var.get(),
            "stop_value": self.stop_value_var.get().strip(),
            "rr_ratio": self.rr_var.get().strip(),
        }
        try:
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._flash_save_button("Saved ✓", GREEN)
        except Exception:
            self._flash_save_button("Save failed", DANGER)

    def _flash_save_button(self, text, color):
        self.save_btn.configure(text=text, text_color=color)
        self.after(1500, lambda: self.save_btn.configure(text="Save Settings", text_color=TEXT_MAIN))


if __name__ == "__main__":
    app = App()
    app.mainloop()
