from __future__ import annotations

from datetime import datetime
from pathlib import Path
from io import BytesIO
import base64
import re
import unicodedata
from typing import Iterable

import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import streamlit.components.v1 as components
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SPREADSHEET_ID = "1pqmFc5FQE6rbCeR321-FHFuTdghpkPGr2XF0irQfjGc"
SHEETS = {
    "contratos": "CONTRATOS VIGENTES",
    "concluidos": "PROCESSOS CONCLUÍDOS",
    "andamento": "CONTRATAÇÕES EM ANDAMENTO",
}


APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "LogoCRFSC.png"


def local_image_base64(path: Path) -> str:
    """Converte uma imagem local para uso seguro no HTML do Streamlit."""
    try:
        return base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""


LOGO_BASE64 = local_image_base64(LOGO_PATH)

st.set_page_config(
    page_title="Gestão de Contratações",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --navy: #123653;
        --blue: #1f6fb2;
        --blue-soft: #eaf3fb;
        --green: #1e8a62;
        --orange: #d97917;
        --red: #c64b4b;
        --ink: #17324d;
        --muted: #66788a;
        --line: #dfe8f0;
        --surface: #ffffff;
        --page: #eef3f8;
    }

    html, body, [class*="css"] {
        font-family: "Segoe UI", Arial, sans-serif;
        max-width: 100%;
        overflow-x: hidden !important;
    }
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main {
        background: linear-gradient(180deg, #edf3f8 0%, #f7f9fc 100%);
        max-width: 100%;
        overflow-x: hidden !important;
    }
    /* Remove a barra superior fixa do Streamlit Cloud para ela não
       sobrepor o cabeçalho institucional do dashboard. */
    header[data-testid="stHeader"],
    [data-testid="stHeader"] {
        display: block !important;
        visibility: visible !important;
        height: 0 !important;
        min-height: 0 !important;
        background: transparent !important;
        pointer-events: none !important;
        overflow: visible !important;
    }

    [data-testid="stHeader"] > div {
        background: transparent !important;
    }

    /*
    Os controles nativos variam entre Chrome, Firefox, Edge e versões do
    Streamlit. Eles ficam invisíveis, mas continuam no DOM para receber o
    clique do botão institucional abaixo.
    */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"] {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 1px !important;
        height: 1px !important;
        min-width: 1px !important;
        min-height: 1px !important;
        opacity: 0 !important;
        visibility: visible !important;
        display: block !important;
        overflow: hidden !important;
        pointer-events: none !important;
        z-index: -1 !important;
    }

    [data-testid="stSidebarCollapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button {
        width: 1px !important;
        height: 1px !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e2d48 0%, #174b73 100%);
        border-right: 1px solid rgba(255,255,255,.08);
        padding-top: .35rem;
    }
    [data-testid="stSidebar"] * {color: #fff;}
    [data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 10px;
        padding: 5px 8px;
        margin-bottom: 3px;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255,255,255,.09);
    }

    .block-container {
        padding-top: 1.35rem !important;
        padding-bottom: .45rem;
        padding-left: 1.15rem;
        padding-right: 1.15rem;
        max-width: 1860px;
    }

    .hero {
        position: relative;
        overflow: visible;
        background: linear-gradient(120deg, #123653 0%, #1f6fb2 72%, #3285c5 100%);
        padding: 13px 20px 14px;
        border-radius: 15px;
        color: white;
        margin: 0 0 11px 0;
        box-shadow: 0 9px 24px rgba(18,54,83,.18);
        min-height: 58px;
        box-sizing: border-box;
    }
    .hero:after {
        content: "";
        position: absolute;
        width: 180px;
        height: 180px;
        border-radius: 50%;
        right: -55px;
        top: -95px;
        background: rgba(255,255,255,.08);
    }
    .hero h1 {
        position: relative;
        z-index: 1;
        font-size: 1.62rem;
        line-height: 1.25;
        margin: 0;
        padding: 0;
        font-weight: 800;
        letter-spacing: -.02em;
        overflow: visible;
    }
    .hero p {margin: 3px 0 0; opacity: .9;}

    .card {
        position: relative;
        overflow: hidden;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 10px 13px 9px 16px;
        box-shadow: 0 5px 16px rgba(20,55,90,.065);
        height: 92px;
        box-sizing: border-box;
    }
    .card:before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 5px;
        background: linear-gradient(180deg, #1f6fb2, #4aa3df);
    }
    .card-label {
        font-size: .72rem;
        text-transform: uppercase;
        letter-spacing: .045em;
        color: #5e7184;
        font-weight: 800;
        line-height: 1.15;
        min-height: 17px;
    }
    .card-value {
        font-size: 1.8rem;
        font-weight: 850;
        color: var(--ink);
        margin-top: 5px;
        line-height: 1;
    }
    .card-note {
        font-size: .72rem;
        color: #7d8c9b;
        margin-top: 5px;
        line-height: 1.1;
        white-space: nowrap;
    }

    .section-panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 15px;
        box-shadow: 0 5px 16px rgba(20,55,90,.06);
        padding: 10px 12px 12px;
        height: 100%;
        box-sizing: border-box;
    }
    .section-title {
        display: flex;
        align-items: center;
        gap: 7px;
        font-size: .98rem;
        font-weight: 850;
        color: var(--ink);
        margin: 0 0 7px 0;
        line-height: 1.2;
    }
    .section-title:before {
        content: "";
        width: 4px;
        height: 17px;
        border-radius: 3px;
        background: #1f6fb2;
        flex: 0 0 auto;
    }

    div[data-testid="stDataFrame"] {
        background: white;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e1e9f0;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box;
    }
    div[data-testid="stDataFrame"] > div {
        max-width: 100% !important;
    }

    div[data-testid="stDataFrame"].responsive-table-fit {
        width: 100% !important;
        max-width: 100% !important;
        min-height: 210px !important;
        overflow: hidden !important;
    }

    div[data-testid="stDataFrame"].responsive-table-fit > div {
        width: 100% !important;
        max-width: 100% !important;
        height: 100% !important;
        max-height: 100% !important;
    }
    div[data-testid="stDataFrame"] [role="gridcell"],
    div[data-testid="stDataFrame"] [role="columnheader"] {text-align: center;}

    div[data-testid="stDataFrame"] [role="columnheader"] {
        background: #d7e8f5 !important;
        color: #123653 !important;
        font-weight: 850 !important;
        border-bottom: 1px solid #bcd2e3 !important;
    }
    div[data-testid="stDataFrame"] [role="columnheader"] > div {
        background: #d7e8f5 !important;
        color: #123653 !important;
        font-weight: 850 !important;
    }

    .overview-table-wrap {
        background: white;
        border: 1px solid #e1e9f0;
        border-radius: 11px;
        overflow: hidden;
        width: 100%;
    }
    table.overview-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
        font-size: .73rem;
    }
    table.overview-table thead th {
        background: linear-gradient(180deg, #e9f2fa 0%, #f2f7fb 100%);
        color: #173f5f;
        font-weight: 850;
        text-align: center;
        padding: 7px 6px;
        border-bottom: 1px solid #d7e3ed;
        line-height: 1.08;
    }
    table.overview-table tbody td {
        text-align: center;
        vertical-align: middle;
        padding: 5px 6px;
        border-bottom: 1px solid #edf1f5;
        line-height: 1.12;
        word-break: break-word;
    }
    table.overview-table tbody tr:last-child td {border-bottom: none;}
    table.overview-table tbody tr:nth-child(even) {background: #f8fbfd;}
    table.overview-table tbody tr:hover {background: #eef6fc;}
    .overview-empty {
        background: white;
        border: 1px solid #e1e9f0;
        border-radius: 11px;
        padding: 22px;
        text-align: center;
        color: #718096;
        font-size: .85rem;
    }

    .row-spacer {height: 8px;}
    .results-inline {
        display: inline-flex;
        align-items: center;
        gap: 9px;
        background: white;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 5px 11px;
        margin: -3px 0 5px;
        color: #62748a;
        font-size: .82rem;
        font-weight: 750;
    }
    .results-inline strong {color: var(--ink); font-size: 1.08rem;}

    .stButton>button {
        border-radius: 10px;
        font-weight: 750;
        background: #2b6cb0;
        color: white;
        border: 1px solid #2b6cb0;
        box-shadow: 0 3px 10px rgba(31,111,178,.2);
    }
    .stButton>button:hover {
        background: #1b588d;
        color: white;
        border-color: #1b588d;
    }

    div[data-testid="stTabs"] {overflow: visible;}
    div[data-testid="stTabs"] > div {overflow: visible;}
    div[data-testid="stTabs"] button[role="tab"] {
        min-height: 44px;
        height: auto;
        padding: 9px 18px;
        overflow: visible;
        margin-top: 2px;
    }
    div[data-testid="stTabs"] button[role="tab"] p {
        white-space: nowrap;
        overflow: visible;
        line-height: 1.3;
        margin: 0;
        padding: 0;
    }


    .top-brand {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:16px;
        min-height:52px;
        margin:0 0 10px 0;
        padding:2px 4px 3px;
        overflow:visible;
        box-sizing:border-box;
    }
    .brand-left {
        display:flex;
        align-items:center;
        gap:13px;
        min-width:0;
        overflow:visible;
    }
    .brand-logo {
        width:142px;
        height:auto;
        max-height:46px;
        object-fit:contain;
        object-position:left center;
        display:block;
        flex:0 0 auto;
    }
    .brand-copy strong {display:block;color:#17324d;font-size:.96rem;line-height:1.05;}
    .brand-copy span {display:block;color:#718096;font-size:.72rem;margin-top:3px;}
    .brand-meta {text-align:right;color:#64778a;font-size:.72rem;line-height:1.35;white-space:nowrap;}
    .brand-meta strong {color:#17324d;font-weight:800;}

    .card {transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;}
    .card:hover {transform:translateY(-2px);box-shadow:0 9px 24px rgba(20,55,90,.12);border-color:#c9dae8;}
    .card-head {display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}
    .card-icon {
        width:28px;height:28px;border-radius:9px;display:flex;align-items:center;justify-content:center;
        font-size:.93rem;flex:0 0 auto;background:#edf5fb;color:#1f6fb2;
    }
    .card.tone-warning:before {background:linear-gradient(180deg,#f3a83b,#d97917);}
    .card.tone-warning .card-icon {background:#fff3df;color:#c96c0b;}
    .card.tone-danger:before {background:linear-gradient(180deg,#e66b6b,#b93f3f);}
    .card.tone-danger .card-icon {background:#fdebec;color:#be3f46;}
    .card.tone-success:before {background:linear-gradient(180deg,#31a97d,#1e805f);}
    .card.tone-success .card-icon {background:#e8f7f1;color:#1d865f;}
    .card.tone-info:before {background:linear-gradient(180deg,#5997cb,#246da8);}

    .sidebar-brand {
        padding:9px 10px 13px;border:1px solid rgba(255,255,255,.12);border-radius:13px;
        background:rgba(255,255,255,.055);margin-bottom:10px;
    }
    .sidebar-brand-title {font-size:1.02rem;font-weight:850;line-height:1.15;}
    .sidebar-brand-sub {font-size:.72rem;opacity:.78;margin-top:5px;line-height:1.3;}
    .sidebar-footer {font-size:.68rem;opacity:.68;text-align:center;margin-top:12px;line-height:1.4;}

    .status-legend {display:flex;gap:7px;flex-wrap:wrap;margin:2px 0 8px;}
    .status-chip {display:inline-flex;align-items:center;gap:5px;padding:4px 8px;border-radius:999px;
        font-size:.68rem;font-weight:750;background:white;border:1px solid #dfe8f0;color:#526679;}
    .status-dot {width:7px;height:7px;border-radius:50%;display:inline-block;}

    @keyframes fadeUp {from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
    .hero,.card,.overview-table-wrap,div[data-testid="stDataFrame"] {animation:fadeUp .28s ease both;}


    @media(max-width: 1100px) {
        .block-container {padding-left: .8rem; padding-right: .8rem;}
        .card {height: 96px;}
        .card-note {white-space: normal;}
    }

    /* No celular, mantém visível o botão que abre/fecha o menu lateral. */
    @media(max-width: 700px) {
        header[data-testid="stHeader"],
        [data-testid="stHeader"] {
            display: block !important;
            visibility: visible !important;
            height: 3.1rem !important;
            min-height: 3.1rem !important;
            background: transparent !important;
            pointer-events: none !important;
        }
        [data-testid="stHeader"] > div {
            background: transparent !important;
        }
        #dashboard-mobile-menu-toggle {
            display: flex !important;
        }
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu {
            display: none !important;
        }
        .block-container {
            padding-top: 3.55rem !important;
            padding-left: .65rem !important;
            padding-right: .65rem !important;
        }
        .top-brand {
            flex-direction: column;
            align-items: flex-start;
            gap: 5px;
        }
        .brand-meta {text-align:left;}
    }


    #dashboard-mobile-menu-toggle {
        display: flex;
        position: fixed;
        top: 10px;
        left: 10px;
        width: 42px;
        height: 42px;
        padding: 0;
        align-items: center;
        justify-content: center;
        border: 1px solid rgba(255,255,255,.30);
        border-radius: 11px;
        background: #123653;
        color: #ffffff;
        font-size: 24px;
        font-weight: 700;
        line-height: 1;
        cursor: pointer;
        box-shadow: 0 5px 18px rgba(18,54,83,.28);
        z-index: 2147483647;
        -webkit-tap-highlight-color: transparent;
    }
    #dashboard-mobile-menu-toggle:hover,
    #dashboard-mobile-menu-toggle:active {
        background: #1f6fb2;
    }

    /* Mantém contador e botão PDF realmente na mesma linha. */
    div[data-testid="stHorizontalBlock"]:has(.results-inline) {
        align-items: center !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.results-inline)
    div[data-testid="stDownloadButton"] {
        margin-top: -1px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.results-inline)
    div[data-testid="stDownloadButton"] > button {
        height: 36px !important;
        min-height: 36px !important;
        padding: 5px 12px !important;
        white-space: nowrap !important;
    }

    div[data-testid="stDownloadButton"] > button {
        background: #1f6fb2 !important;
        color: white !important;
        border: 1px solid #1f6fb2 !important;
        border-radius: 9px !important;
        font-weight: 750 !important;
        min-height: 38px !important;
    }
    div[data-testid="stDownloadButton"] > button:hover {
        background: #185b91 !important;
        border-color: #185b91 !important;
        color: white !important;
    }

    /*
    Contador e PDF na mesma linha, ambos compactos.
    O contador preserva exatamente o tamanho natural anterior.
    */
    .st-key-counter_pdf_andamento [data-testid="stHorizontalBlock"],
    .st-key-counter_pdf_concluidos [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        justify-content: flex-start !important;
        align-items: center !important;
        gap: .38rem !important;
        width: 100% !important;
    }

    .st-key-counter_pdf_andamento [data-testid="stColumn"]:first-child,
    .st-key-counter_pdf_concluidos [data-testid="stColumn"]:first-child {
        flex: 0 0 auto !important;
        width: fit-content !important;
        max-width: fit-content !important;
        min-width: 0 !important;
    }

    .st-key-counter_pdf_andamento [data-testid="stColumn"]:last-child,
    .st-key-counter_pdf_concluidos [data-testid="stColumn"]:last-child {
        flex: 0 0 124px !important;
        width: 124px !important;
        max-width: 124px !important;
        min-width: 124px !important;
    }

    .st-key-counter_pdf_andamento .results-inline,
    .st-key-counter_pdf_concluidos .results-inline {
        width: auto !important;
        min-height: unset !important;
        margin: -3px 0 5px !important;
        box-sizing: border-box !important;
        white-space: nowrap !important;
    }

    .st-key-counter_pdf_andamento div[data-testid="stDownloadButton"],
    .st-key-counter_pdf_concluidos div[data-testid="stDownloadButton"] {
        margin: -3px 0 5px !important;
    }

    .st-key-counter_pdf_andamento div[data-testid="stDownloadButton"] > button,
    .st-key-counter_pdf_concluidos div[data-testid="stDownloadButton"] > button {
        height: 34px !important;
        min-height: 34px !important;
        padding: 4px 9px !important;
        font-size: .73rem !important;
    }

    @media(max-width: 700px) {
        .st-key-counter_pdf_andamento [data-testid="stHorizontalBlock"],
        .st-key-counter_pdf_concluidos [data-testid="stHorizontalBlock"] {
            gap: .28rem !important;
        }

        .st-key-counter_pdf_andamento [data-testid="stColumn"]:last-child,
        .st-key-counter_pdf_concluidos [data-testid="stColumn"]:last-child {
            flex: 0 0 102px !important;
            width: 102px !important;
            max-width: 102px !important;
            min-width: 102px !important;
        }

        .st-key-counter_pdf_andamento div[data-testid="stDownloadButton"] > button,
        .st-key-counter_pdf_concluidos div[data-testid="stDownloadButton"] > button {
            padding: 4px 5px !important;
            font-size: .66rem !important;
        }

        .st-key-counter_pdf_andamento .results-inline,
        .st-key-counter_pdf_concluidos .results-inline {
            padding: 5px 8px !important;
            font-size: .72rem !important;
            gap: 5px !important;
        }

        .st-key-counter_pdf_andamento .results-inline strong,
        .st-key-counter_pdf_concluidos .results-inline strong {
            font-size: .96rem !important;
        }
    }


    /* Contador e botão PDF com exatamente a mesma altura. */
    .st-key-counter_pdf_andamento .results-inline,
    .st-key-counter_pdf_concluidos .results-inline {
        height: 34px !important;
        min-height: 34px !important;
        max-height: 34px !important;
        display: inline-flex !important;
        align-items: center !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        margin-top: -3px !important;
        margin-bottom: 5px !important;
        line-height: 1 !important;
    }

    .st-key-counter_pdf_andamento div[data-testid="stDownloadButton"],
    .st-key-counter_pdf_concluidos div[data-testid="stDownloadButton"] {
        height: 34px !important;
        min-height: 34px !important;
        max-height: 34px !important;
        margin-top: -3px !important;
        margin-bottom: 5px !important;
    }

    .st-key-counter_pdf_andamento div[data-testid="stDownloadButton"] > button,
    .st-key-counter_pdf_concluidos div[data-testid="stDownloadButton"] > button {
        height: 34px !important;
        min-height: 34px !important;
        max-height: 34px !important;
        margin: 0 !important;
        line-height: 1 !important;
    }

    @media(max-width: 700px) {
        /*
        Em telas pequenas, os quatro filtros formam uma grade 2x2.
        No desktop, o layout original de quatro filtros na mesma linha permanece.
        */
        .st-key-filtros_concluidos_mobile [data-testid="stHorizontalBlock"],
        .st-key-filtros_andamento_mobile [data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
            gap: .45rem .55rem !important;
            width: 100% !important;
            align-items: start !important;
        }

        .st-key-filtros_concluidos_mobile [data-testid="stColumn"],
        .st-key-filtros_andamento_mobile [data-testid="stColumn"] {
            width: 100% !important;
            min-width: 0 !important;
            max-width: none !important;
            flex: none !important;
        }

        .st-key-filtros_concluidos_mobile [data-testid="stSelectbox"],
        .st-key-filtros_concluidos_mobile [data-testid="stTextInput"],
        .st-key-filtros_andamento_mobile [data-testid="stSelectbox"],
        .st-key-filtros_andamento_mobile [data-testid="stTextInput"] {
            width: 100% !important;
            min-width: 0 !important;
        }

        .st-key-filtros_concluidos_mobile [data-testid="stWidgetLabel"],
        .st-key-filtros_andamento_mobile [data-testid="stWidgetLabel"] {
            font-size: .84rem !important;
        }

        /* Mantém contador e PDF lado a lado e perfeitamente alinhados. */
        .st-key-counter_pdf_andamento [data-testid="stHorizontalBlock"],
        .st-key-counter_pdf_concluidos [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
        }

        .st-key-counter_pdf_andamento .results-inline,
        .st-key-counter_pdf_concluidos .results-inline,
        .st-key-counter_pdf_andamento div[data-testid="stDownloadButton"],
        .st-key-counter_pdf_concluidos div[data-testid="stDownloadButton"],
        .st-key-counter_pdf_andamento div[data-testid="stDownloadButton"] > button,
        .st-key-counter_pdf_concluidos div[data-testid="stDownloadButton"] > button {
            height: 34px !important;
            min-height: 34px !important;
            max-height: 34px !important;
        }
    }


    @media(min-width: 701px) {
        #dashboard-mobile-menu-toggle {
            top: 10px;
            left: 10px;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


def norm(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text.strip().upper())


def find_col(df: pd.DataFrame, names: Iterable[str], fallback: int | None = None) -> str | None:
    lookup = {norm(c): c for c in df.columns}
    wanted = [norm(n) for n in names]
    for candidate in wanted:
        if candidate in lookup:
            return lookup[candidate]
    for key, original in lookup.items():
        if any(w in key or key in w for w in wanted if len(w) > 3):
            return original
    if fallback is not None and fallback < len(df.columns):
        return df.columns[fallback]
    return None


def make_unique(columns: list[object]) -> list[str]:
    """Garante nomes de colunas válidos e únicos."""
    seen: dict[str, int] = {}
    result: list[str] = []
    for value in columns:
        base = str(value).strip() if pd.notna(value) else ""
        if not base or base.lower() == "nan":
            base = "COLUNA"
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.append(base if count == 0 else f"{base} {count + 1}")
    return result


def prepare_sheet(raw: pd.DataFrame, sheet_key: str) -> pd.DataFrame:
    """Promove a linha correta para cabeçalho sem perder colunas úteis."""
    header_row = 1 if sheet_key == "contratos" else 0
    if raw.empty or header_row >= len(raw):
        return pd.DataFrame()
    df = raw.iloc[header_row + 1:].copy()
    df.columns = make_unique(raw.iloc[header_row].tolist())
    df = df.dropna(how="all").reset_index(drop=True)

    # A primeira coluna das três abas é apenas numeração/controle visual.
    if len(df.columns):
        first = df.columns[0]
        first_norm = norm(first)
        if first_norm in {".", "COLUNA", "UNNAMED: 0"} or first_norm.startswith("COLUNA"):
            df = df.drop(columns=[first])

    # Na aba de concluídos, a coluna de dias não possui título na planilha.
    if sheet_key == "concluidos":
        unnamed = [c for c in df.columns if norm(c).startswith("COLUNA")]
        if unnamed:
            df = df.rename(columns={unnamed[-1]: "DIAS"})
    return df


def get_google_credentials() -> Credentials:
    """Cria credenciais usando o grupo [gcp_service_account] do Streamlit Secrets."""
    if "gcp_service_account" not in st.secrets:
        raise KeyError(
            "As credenciais não foram encontradas. Configure [gcp_service_account] "
            "em Settings → Secrets no Streamlit Cloud."
        )

    service_account_info = dict(st.secrets["gcp_service_account"])
    required = {"type", "project_id", "private_key", "client_email", "token_uri"}
    missing = sorted(required.difference(service_account_info))
    if missing:
        raise KeyError(
            "Campos ausentes nos Secrets: " + ", ".join(missing)
        )

    # Corrige chaves coladas com \n literal ou com quebras já interpretadas pelo TOML.
    private_key = str(service_account_info["private_key"])
    service_account_info["private_key"] = private_key.replace("\\n", "\n")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    return Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes,
    )


@st.cache_data(ttl=120, show_spinner=False)
def load_workbook() -> dict[str, pd.DataFrame]:
    """Lê as abas da planilha privada pela conta de serviço do Google."""
    credentials = get_google_credentials()
    client = gspread.authorize(credentials)

    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
    except gspread.exceptions.SpreadsheetNotFound as exc:
        raise PermissionError(
            "A conta de serviço não tem acesso à planilha. Compartilhe a planilha "
            "com o client_email informado nos Secrets."
        ) from exc

    result: dict[str, pd.DataFrame] = {}
    for key, sheet_name in SHEETS.items():
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound as exc:
            raise KeyError(f'A aba "{sheet_name}" não foi encontrada.') from exc

        values = worksheet.get_all_values()
        raw = pd.DataFrame(values)
        result[key] = prepare_sheet(raw, key)

    return result


def numeric(series: pd.Series) -> pd.Series:
    """Converte uma coluna em números, preservando exatamente o índice original."""
    converted = series.copy()
    if not pd.api.types.is_numeric_dtype(converted):
        converted = (
            converted.astype(str)
            .str.strip()
            .str.replace(r"[^0-9,.-]", "", regex=True)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
    result = pd.to_numeric(converted, errors="coerce")
    result.index = series.index
    return result


def format_date_br(series: pd.Series) -> pd.Series:
    """Formata datas no padrão brasileiro, preservando vazios e textos não reconhecidos."""
    original = series.copy()
    converted = pd.to_datetime(original, errors="coerce", dayfirst=True)
    formatted = converted.dt.strftime("%d/%m/%Y")
    fallback = original.where(original.notna(), "").astype(str).replace({"NaT": "", "nan": ""})
    return formatted.where(converted.notna(), fallback)



def parse_money_value(value: object) -> float | None:
    """Converte números e textos monetários brasileiros sem distorcer os centavos."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none"}:
        return None

    text = re.sub(r"[^0-9,.-]", "", text)
    if not text:
        return None

    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "." in text:
        # Um ponto seguido de duas casas é tratado como decimal.
        if not re.search(r"\.\d{1,2}$", text):
            text = text.replace(".", "")

    try:
        return float(text)
    except ValueError:
        return None


def format_currency_br(series: pd.Series) -> pd.Series:
    """Formata valores como moeda brasileira: R$ 1.234,56."""
    def format_one(value: object) -> str:
        parsed = parse_money_value(value)
        if parsed is None:
            return "" if value is None or pd.isna(value) else str(value)
        formatted = f"{parsed:,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"

    return series.map(format_one)


def format_contract_columns_br(df: pd.DataFrame) -> pd.DataFrame:
    """Formata datas e valores da tabela completa de contratos."""
    out = df.copy()
    for col in out.columns:
        normalized = norm(col)

        is_date = (
            "DATA" in normalized
            or "VIGENCIA" in normalized
            or "APOSTILAMENTO" in normalized
        ) and "DIA" not in normalized

        is_money = any(
            term in normalized
            for term in ["VALOR", "PRECO", "PREÇO", "CUSTO"]
        )

        if is_date:
            out[col] = format_date_br(out[col])
        elif is_money:
            out[col] = format_currency_br(out[col])

    return out


def aligned_numeric(df: pd.DataFrame, col: str | None) -> pd.Series:
    """Retorna números sempre alinhados ao DataFrame, mesmo se a coluna não existir."""
    if not col or col not in df.columns:
        return pd.Series(float("nan"), index=df.index, dtype="float64")
    selected = df.loc[:, col]
    # Se houver cabeçalhos duplicados, usa a primeira coluna correspondente.
    if isinstance(selected, pd.DataFrame):
        selected = selected.iloc[:, 0]
    return numeric(selected).reindex(df.index)


def aligned_mask(df: pd.DataFrame, condition: pd.Series) -> pd.Series:
    """Garante que máscaras booleanas possam ser usadas com .loc sem desalinhamento."""
    return condition.reindex(df.index, fill_value=False).fillna(False).astype(bool)





def install_persistent_mobile_menu() -> None:
    """Cria um botão leve para abrir/recolher o menu em qualquer navegador."""
    components.html(
        """
        <script>
        (() => {
            const win = window.parent;
            const doc = win.document;
            const BUTTON_ID = "dashboard-mobile-menu-toggle";

            function sidebarIsOpen() {
                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (!sidebar) return false;

                const rect = sidebar.getBoundingClientRect();
                const style = win.getComputedStyle(sidebar);

                return (
                    rect.width > 80 &&
                    rect.right > 1 &&
                    style.display !== "none" &&
                    style.visibility !== "hidden"
                );
            }

            function getNativeToggle() {
                const selectors = [
                    '[data-testid="stSidebarCollapsedControl"] button',
                    '[data-testid="stSidebarCollapseButton"] button',
                    '[data-testid="stSidebarCollapsedControl"]',
                    '[data-testid="stSidebarCollapseButton"]',
                    'button[aria-label="Open sidebar"]',
                    'button[aria-label="Close sidebar"]',
                    'button[aria-label="Abrir barra lateral"]',
                    'button[aria-label="Fechar barra lateral"]'
                ];

                for (const selector of selectors) {
                    const element = doc.querySelector(selector);
                    if (element) return element;
                }

                return null;
            }

            function updateButton(button) {
                const open = sidebarIsOpen();
                button.textContent = open ? "×" : "☰";
                button.title = open ? "Recolher menu" : "Abrir menu";
                button.setAttribute("aria-label", button.title);
                button.style.display = "flex";
            }

            function ensureButton() {
                let button = doc.getElementById(BUTTON_ID);

                if (!button) {
                    button = doc.createElement("button");
                    button.id = BUTTON_ID;
                    button.type = "button";

                    button.addEventListener("click", (event) => {
                        event.preventDefault();
                        event.stopPropagation();

                        const toggle = getNativeToggle();
                        if (toggle) {
                            toggle.click();
                        }

                        win.setTimeout(() => updateButton(button), 120);
                    });

                    doc.body.appendChild(button);
                }

                updateButton(button);
                return button;
            }

            function closeMenuAfterSelection() {
                if (!win.matchMedia("(max-width: 700px)").matches) return;
                if (!sidebarIsOpen()) return;

                const toggle = getNativeToggle();
                if (toggle) {
                    win.setTimeout(() => toggle.click(), 80);
                }
            }

            function bindNavigation() {
                const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                if (!sidebar) return;

                const options = sidebar.querySelectorAll(
                    '[role="radiogroup"] label, [role="radio"]'
                );

                options.forEach((option) => {
                    if (option.dataset.dashboardCloseBound === "true") return;

                    option.dataset.dashboardCloseBound = "true";
                    option.addEventListener(
                        "click",
                        closeMenuAfterSelection,
                        true
                    );
                });
            }

            const button = ensureButton();
            bindNavigation();

            // Repetições curtas apenas durante o carregamento inicial.
            // Não há observador contínuo nem ciclo permanente.
            [200, 700, 1600].forEach((delay) => {
                win.setTimeout(() => {
                    ensureButton();
                    bindNavigation();
                    updateButton(button);
                }, delay);
            });
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def install_live_native_search(debounce_ms: int = 350) -> None:
    """Faz os campos nativos de pesquisa filtrarem após uma breve pausa."""
    components.html(
        f"""
        <script>
        (() => {{
            const parentWindow = window.parent;
            const parentDocument = parentWindow.document;
            const DEBOUNCE = {int(debounce_ms)};
            const SEARCH_LABELS = [
                "Pesquisar empresa ou objeto",
                "Pesquisar no objeto"
            ];

            function normalize(text) {{
                return (text || "")
                    .trim()
                    .toLocaleLowerCase("pt-BR");
            }}

            function isSearchInput(input) {{
                const widget = input.closest(
                    'div[data-testid="stTextInput"]'
                );
                if (!widget) return false;

                const label = widget.querySelector("label");
                const labelText = normalize(label?.innerText);
                return SEARCH_LABELS.some(
                    item => labelText === normalize(item)
                );
            }}

            function submitInput(input) {{
                if (!input || !parentDocument.contains(input)) return;

                const value = input.value || "";
                const lastSubmitted = input.dataset.lastLiveSubmitted ?? "";

                if (value === lastSubmitted) return;
                input.dataset.lastLiveSubmitted = value;

                sessionStorage.setItem(
                    "dashboard-live-search-focus",
                    input.getAttribute("aria-label") || ""
                );

                input.dispatchEvent(
                    new KeyboardEvent("keydown", {{
                        key: "Enter",
                        code: "Enter",
                        keyCode: 13,
                        which: 13,
                        bubbles: true,
                        cancelable: true
                    }})
                );
                input.dispatchEvent(
                    new KeyboardEvent("keyup", {{
                        key: "Enter",
                        code: "Enter",
                        keyCode: 13,
                        which: 13,
                        bubbles: true,
                        cancelable: true
                    }})
                );

                input.blur();
            }}

            function bindInputs() {{
                const inputs = parentDocument.querySelectorAll(
                    'div[data-testid="stTextInput"] input'
                );

                inputs.forEach(input => {{
                    if (!isSearchInput(input)) return;
                    if (input.dataset.liveSearchBound === "true") return;

                    input.dataset.liveSearchBound = "true";
                    input.dataset.lastLiveSubmitted = input.value || "";

                    let timer = null;

                    input.addEventListener("input", () => {{
                        parentWindow.clearTimeout(timer);
                        timer = parentWindow.setTimeout(
                            () => submitInput(input),
                            DEBOUNCE
                        );
                    }});
                }});

                const wantedLabel = sessionStorage.getItem(
                    "dashboard-live-search-focus"
                );
                if (wantedLabel) {{
                    const target = [...inputs].find(
                        input =>
                            isSearchInput(input) &&
                            (input.getAttribute("aria-label") || "") === wantedLabel
                    );
                    if (target) {{
                        sessionStorage.removeItem(
                            "dashboard-live-search-focus"
                        );
                        target.focus();
                        const end = target.value.length;
                        target.setSelectionRange(end, end);
                    }}
                }}
            }}

            if (!parentWindow.__dashboardLiveSearchInstalled) {{
                parentWindow.__dashboardLiveSearchInstalled = true;

                const observer = new MutationObserver(bindInputs);
                observer.observe(parentDocument.body, {{
                    childList: true,
                    subtree: true
                }});

                parentWindow.__dashboardLiveSearchObserver = observer;
            }}

            bindInputs();
            parentWindow.setTimeout(bindInputs, 150);
            parentWindow.setTimeout(bindInputs, 500);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )

def install_responsive_table_resizer(
    bottom_margin: int = 18,
    min_height: int = 220,
    max_height: int = 760,
) -> None:
    """Ajusta as tabelas à altura disponível da janela do navegador.

    O cálculo é refeito ao abrir a página, redimensionar a janela, alterar
    o zoom do navegador ou trocar de aba. A rolagem permanece dentro da
    tabela, evitando barras externas na página.
    """
    components.html(
        f"""
        <script>
        (() => {{
            const parentWindow = window.parent;
            const parentDocument = parentWindow.document;
            const MIN_HEIGHT = {int(min_height)};
            const MAX_HEIGHT = {int(max_height)};
            const BOTTOM_MARGIN = {int(bottom_margin)};

            function isVisible(element) {{
                if (!element) return false;
                const style = parentWindow.getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return (
                    style.display !== "none" &&
                    style.visibility !== "hidden" &&
                    rect.width > 0 &&
                    rect.height >= 0
                );
            }}

            function resizeTables() {{
                const viewportHeight =
                    parentWindow.visualViewport?.height ||
                    parentWindow.innerHeight ||
                    parentDocument.documentElement.clientHeight;

                const tables = parentDocument.querySelectorAll(
                    'div[data-testid="stDataFrame"]'
                );

                tables.forEach((table) => {{
                    if (!isVisible(table)) return;

                    const rect = table.getBoundingClientRect();
                    const available = Math.floor(
                        viewportHeight - rect.top - BOTTOM_MARGIN
                    );
                    const target = Math.max(
                        MIN_HEIGHT,
                        Math.min(MAX_HEIGHT, available)
                    );

                    table.classList.add("responsive-table-fit");
                    table.style.setProperty(
                        "height",
                        `${{target}}px`,
                        "important"
                    );
                    table.style.setProperty(
                        "max-height",
                        `${{target}}px`,
                        "important"
                    );

                    const directChild = table.firstElementChild;
                    if (directChild) {{
                        directChild.style.setProperty(
                            "height",
                            "100%",
                            "important"
                        );
                        directChild.style.setProperty(
                            "max-height",
                            "100%",
                            "important"
                        );
                    }}
                }});

                // Faz o grid recalcular a área interna após a mudança.
                parentWindow.dispatchEvent(new Event("resize"));
            }}

            let resizeTimer;
            function scheduleResize() {{
                parentWindow.clearTimeout(resizeTimer);
                resizeTimer = parentWindow.setTimeout(resizeTables, 60);
            }}

            if (!parentWindow.__dashboardResponsiveTablesInstalled) {{
                parentWindow.__dashboardResponsiveTablesInstalled = true;

                parentWindow.addEventListener("resize", scheduleResize);
                parentWindow.visualViewport?.addEventListener(
                    "resize",
                    scheduleResize
                );

                const observer = new MutationObserver(scheduleResize);
                observer.observe(parentDocument.body, {{
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeFilter: ["style", "class", "aria-selected"],
                }});

                if ("ResizeObserver" in parentWindow) {{
                    const resizeObserver = new ResizeObserver(scheduleResize);
                    resizeObserver.observe(parentDocument.documentElement);
                    resizeObserver.observe(parentDocument.body);
                    parentWindow.__dashboardTableResizeObserver = resizeObserver;
                }}

                parentWindow.__dashboardTableMutationObserver = observer;
            }}

            scheduleResize();
            parentWindow.setTimeout(resizeTables, 180);
            parentWindow.setTimeout(resizeTables, 500);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def _pdf_text(value: object) -> str:
    """Converte valores da tabela em texto seguro para o PDF."""
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%d/%m/%Y")
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def dataframe_to_pdf(df: pd.DataFrame, title: str) -> bytes:
    """Gera um PDF paisagem, paginado e com cabeçalho repetido."""
    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    margin = 11 * mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        rightMargin=margin,
        leftMargin=margin,
        topMargin=11 * mm,
        bottomMargin=11 * mm,
        title=title,
        author="CRF/SC - Comissão de Compras e Contratações",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PdfTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#123653"),
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )
    info_style = ParagraphStyle(
        "PdfInfo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#526679"),
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )
    header_style = ParagraphStyle(
        "PdfHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=8.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#123653"),
    )
    cell_style = ParagraphStyle(
        "PdfCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8.2,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#26394d"),
    )

    clean = df.copy().reset_index(drop=True).fillna("")
    story = [
        Paragraph(title, title_style),
        Paragraph(
            f"Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} - "
            f"{len(clean)} registro(s)",
            info_style,
        ),
    ]

    if clean.empty:
        story.append(Paragraph("Nenhum registro encontrado.", cell_style))
        doc.build(story)
        return buffer.getvalue()

    headers = [Paragraph(_pdf_text(column), header_style) for column in clean.columns]
    rows = [headers]
    for _, row in clean.iterrows():
        rows.append([Paragraph(_pdf_text(value), cell_style) for value in row.tolist()])

    usable_width = page_width - (2 * margin)
    text_lengths = []
    for column in clean.columns:
        sample = clean[column].astype(str).head(40).tolist()
        longest = max([len(str(column))] + [min(len(value), 70) for value in sample])
        text_lengths.append(max(6, longest))
    total_weight = sum(text_lengths) or 1
    min_width = 18 * mm
    raw_widths = [max(min_width, usable_width * weight / total_weight) for weight in text_lengths]
    scale = usable_width / sum(raw_widths)
    col_widths = [width * scale for width in raw_widths]

    table = Table(
        rows,
        colWidths=col_widths,
        repeatRows=1,
        hAlign="CENTER",
        splitByRow=1,
    )
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dcebf7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#123653")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c9d7e3")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for row_number in range(1, len(rows)):
        background = "#ffffff" if row_number % 2 else "#f3f7fa"
        table_style.append(
            ("BACKGROUND", (0, row_number), (-1, row_number), colors.HexColor(background))
        )
    table.setStyle(TableStyle(table_style))
    story.extend([table, Spacer(1, 2 * mm)])
    doc.build(story)
    return buffer.getvalue()


def pdf_download_button(df: pd.DataFrame, title: str, file_name: str, key: str) -> None:
    """Exibe o botão para baixar exatamente a lista filtrada da tela."""
    st.download_button(
        label="📄 Baixar PDF",
        data=dataframe_to_pdf(df, title),
        file_name=file_name,
        mime="application/pdf",
        key=key,
        use_container_width=False,
    )

def display_table(
    df: pd.DataFrame,
    height: int = 420,
    dynamic_height: bool = False,
    column_widths: dict[str, str | int] | None = None,
    font_size: int = 12,
    responsive: bool = True,
    responsive_bottom_margin: int = 18,
    responsive_min_height: int = 220,
    responsive_max_height: int = 760,
) -> None:
    """Exibe tabela corporativa, centralizada e com destaques de prioridade."""
    shown_height = height
    if dynamic_height:
        shown_height = min(height, max(150, 38 * (len(df) + 1)))

    # Uma área inicial ampla evita que o grid fique preso à altura fixa.
    # O ajuste definitivo é feito no navegador logo após a renderização.
    if responsive:
        shown_height = max(shown_height, min(responsive_max_height, 650))

    styled = df.style.set_properties(**{
        "text-align": "center",
        "vertical-align": "middle",
        "font-size": f"{font_size}px",
        "white-space": "normal",
        "word-break": "break-word",
        "line-height": "1.15",
    })
    styled = styled.set_table_styles([
        {"selector": "th", "props": [
            ("text-align", "center"), ("vertical-align", "middle"),
            ("background-color", "#dcebf7"), ("color", "#173f5f"),
            ("font-weight", "800"), ("border-bottom", "1px solid #d7e3ed")
        ]},
    ])

    # Aplica faixas alternadas em todas as tabelas, inclusive no componente interativo.
    def alternating_rows(row: pd.Series) -> list[str]:
        position = df.index.get_loc(row.name)
        background = "background-color:#f7fafc" if position % 2 else "background-color:#ffffff"
        return [background] * len(row)

    styled = styled.apply(alternating_rows, axis=1)

    day_columns = [c for c in df.columns if "DIA" in norm(c)]
    for col in day_columns:
        try:
            values = numeric(df[col])
            def day_color(value):
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    return ""
                if number < 0:
                    return "background-color:#fdebec;color:#a93038;font-weight:800"
                if number <= 30:
                    return "background-color:#fff0dd;color:#a65a08;font-weight:800"
                if number <= 60:
                    return "background-color:#fff8df;color:#80620a;font-weight:750"
                return "background-color:#eaf7f1;color:#1d7355;font-weight:750"
            styled = styled.map(day_color, subset=[col])
        except Exception:
            pass

    column_config = {}
    if column_widths:
        for column, width in column_widths.items():
            if column in df.columns:
                column_config[column] = st.column_config.TextColumn(
                    column,
                    width=width,
                )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=shown_height,
        column_config=column_config or None,
    )

    if responsive:
        install_responsive_table_resizer(
            bottom_margin=responsive_bottom_margin,
            min_height=responsive_min_height,
            max_height=responsive_max_height,
        )


def display_overview_table(df: pd.DataFrame) -> None:
    """Tabela integral e compacta da Visão geral, sem qualquer rolagem interna."""
    if df.empty:
        st.markdown('<div class="overview-empty">Nenhum registro encontrado.</div>', unsafe_allow_html=True)
        return
    clean = df.copy().fillna("")
    html = clean.to_html(index=False, classes="overview-table", border=0, escape=True)
    st.markdown(f'<div class="overview-table-wrap">{html}</div>', unsafe_allow_html=True)


def metric_card(
    label: str,
    value: int | str,
    note: str = "",
    icon: str = "▦",
    tone: str = "info",
) -> None:
    st.markdown(
        f'<div class="card tone-{tone}"><div class="card-head">'
        f'<div class="card-label">{label}</div><div class="card-icon">{icon}</div></div>'
        f'<div class="card-value">{value}</div><div class="card-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def safe_values(df: pd.DataFrame, col: str | None) -> list[str]:
    if not col:
        return []
    vals = df[col].dropna().astype(str).str.strip()
    return sorted(v for v in vals.unique() if v and v.lower() != "nan")


def contains_filter(df: pd.DataFrame, col: str | None, text: str) -> pd.Series:
    if not text or not col:
        return pd.Series(True, index=df.index)
    return df[col].fillna("").astype(str).str.contains(text, case=False, na=False, regex=False)


def status_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    cols = {
        "AGUARDANDO": find_col(out, ["AGUARDANDO"], 6),
        "PLANEJAMENTO": find_col(out, ["PLANEJAMENTO"], 7),
        "LICITAÇÃO": find_col(out, ["LICITAÇÃO", "LICITACAO"], 8),
        "GESTÃO CONTRATO": find_col(out, ["GESTÃO CONTRATO", "GESTAO CONTRATO"], 9),
    }
    def choose(row):
        for status in ["GESTÃO CONTRATO", "LICITAÇÃO", "PLANEJAMENTO", "AGUARDANDO"]:
            col = cols[status]
            if col and pd.notna(row.get(col)) and str(row.get(col)).strip():
                return pd.Series([status, str(row.get(col)).strip()])
        return pd.Series(["SEM STATUS", ""])
    out[["STATUS", "INFORMAÇÃO / ANDAMENTO"]] = out.apply(choose, axis=1)
    return out


def page_header(title: str, subtitle: str = "") -> None:
    now = datetime.now()
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    logo_html = (
        f'<img class="brand-logo" src="data:image/png;base64,{LOGO_BASE64}" '
        f'alt="CRF/SC">'
        if LOGO_BASE64
        else '<div class="brand-copy"><strong>CRF/SC</strong></div>'
    )
    st.markdown(
        f'<div class="top-brand"><div class="brand-left">{logo_html}'
        f'<div class="brand-copy"><strong>Gestão de Contratações</strong>'
        f'<span>Comissão de Compras e Contratações</span></div></div>'
        f'<div class="brand-meta"><strong>{now.strftime("%d/%m/%Y")}</strong><br>'
        f'Atualizado às {now.strftime("%H:%M")}</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="hero"><h1>{title}</h1>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand"><div class="sidebar-brand-title">📊 Gestão de Contratações</div>'
        '<div class="sidebar-brand-sub">CRF/SC • acompanhamento de contratos e processos</div></div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Navegação",
        ["Visão geral", "Em andamento", "Contratos", "Processos concluídos"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("🔄 Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown('<div class="sidebar-footer">Dados sincronizados com o Google Planilhas</div>', unsafe_allow_html=True)

# Mantém o botão hambúrguer sempre disponível no celular.
install_persistent_mobile_menu()

# Mantém o campo nativo do Streamlit e atualiza a pesquisa após breve pausa.
install_live_native_search(debounce_ms=350)

try:
    with st.spinner("Conectando à planilha..."):
        data = load_workbook()
except Exception as exc:
    page_header("Não foi possível abrir a planilha", "Confira a permissão pública e os nomes das abas.")
    st.error(str(exc))
    st.info("Confira os Secrets do Streamlit e se a planilha foi compartilhada com o e-mail da conta de serviço.")
    st.stop()

contratos = data["contratos"]
concluidos = data["concluidos"]
andamento = status_data(data["andamento"])

# Campos identificados de forma tolerante a pequenas alterações nos cabeçalhos.
c_empresa = find_col(contratos, ["EMPRESA"], 6)
c_fiscal = find_col(contratos, ["FISCAL DE CONTRATO", "FISCAL"], 1)
c_status = find_col(contratos, ["STATUS"], 12)
c_objeto = find_col(contratos, ["OBJETO"], 5)
c_apost_data = find_col(contratos, ["PRÓXIMO APOSTILAMENTO ANUAL", "PROXIMO APOSTILAMENTO ANUAL"], 8)
# Existem duas colunas chamadas "Dias a Vencer": a primeira é do apostilamento
# e a segunda é da vigência final. make_unique renomeia a segunda para "Dias a Vencer 2".
c_apost_dias = find_col(contratos, ["DIAS A VENCER"], 8)
c_contrato_dias = find_col(
    contratos,
    ["DIAS A VENCER 2", "DIAS VENCIMENTO CONTRATO", "DIAS A VENCER CONTRATO"],
    10,
)

apost_dias = aligned_numeric(contratos, c_apost_dias)
contrato_dias = aligned_numeric(contratos, c_contrato_dias)

if page == "Visão geral":
    page_header("Dashboard de Contratações")

    counts = andamento["STATUS"].value_counts().rename_axis("Status").reset_index(name="Quantidade")

    urgent = contratos.loc[
        aligned_mask(contratos, (contrato_dias >= 0) & (contrato_dias <= 90))
    ].copy()
    if c_objeto and c_contrato_dias:
        urgent = urgent[[c_objeto, c_contrato_dias]].rename(
            columns={c_objeto: "OBJETO", c_contrato_dias: "DIAS"}
        )
        urgent["DIAS"] = numeric(urgent["DIAS"])
        urgent = urgent.sort_values("DIAS")

    ap = contratos.loc[
        aligned_mask(contratos, (apost_dias >= 0) & (apost_dias <= 60))
    ].copy()
    fields = [x for x in [c_empresa, c_apost_data, c_apost_dias] if x]
    if fields:
        ap = ap[fields].copy()
        ap.columns = ["EMPRESA", "PRÓXIMO APOSTILAMENTO", "DIAS"][:len(fields)]
        if "PRÓXIMO APOSTILAMENTO" in ap:
            ap["PRÓXIMO APOSTILAMENTO"] = format_date_br(ap["PRÓXIMO APOSTILAMENTO"])
        if "DIAS" in ap:
            ap["DIAS"] = numeric(ap["DIAS"])
            ap = ap.sort_values("DIAS")

    # Duas áreas independentes evitam que a tabela superior crie espaço vazio
    # abaixo dos cards. O gráfico começa imediatamente após os indicadores.
    dashboard_left, dashboard_right = st.columns([1.06, 1.0], gap="large")

    with dashboard_left:
        kpi1, kpi2, kpi3 = st.columns(3, gap="medium")
        with kpi1:
            metric_card(
                "Contratos Vigentes",
                len(contratos),
                "Registros na planilha",
                "▤",
                "info",
            )
        with kpi2:
            metric_card(
                "Apostilamentos em 60 Dias",
                int(((apost_dias >= 0) & (apost_dias <= 60)).sum()),
                "Exigem atenção",
                "⚠",
                "warning",
            )
        with kpi3:
            metric_card(
                "Contratos em 90 Dias",
                int(((contrato_dias >= 0) & (contrato_dias <= 90)).sum()),
                "Novo processo",
                "⏱",
                "danger",
            )

        st.markdown('<div class="row-spacer"></div>', unsafe_allow_html=True)

        indicators_col, chart_col = st.columns([0.62, 1.38], gap="medium")

        with indicators_col:
            metric_card(
                "Em Andamento",
                len(andamento),
                "Contratações abertas",
                "↻",
                "success",
            )
            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
            metric_card(
                "Processos Concluídos",
                len(concluidos),
                "Histórico a partir 05/2023",
                "✓",
                "info",
            )

        with chart_col:
            st.markdown(
                '<div class="section-title">Contratações em Andamento</div>',
                unsafe_allow_html=True,
            )
            stage_colors = {
                "AGUARDANDO": "#8da0b3",
                "PLANEJAMENTO": "#e49a32",
                "LICITAÇÃO": "#2f80c5",
                "GESTÃO CONTRATO": "#23966f",
                "SEM STATUS": "#c4ced8",
            }
            fig = px.pie(
                counts,
                names="Status",
                values="Quantidade",
                hole=.66,
                color="Status",
                color_discrete_map=stage_colors,
            )
            fig.update_traces(
                textposition="inside",
                textinfo="value",
                marker=dict(line=dict(color="#ffffff", width=2)),
                hovertemplate="<b>%{label}</b><br>%{value} processo(s)<br>%{percent}<extra></extra>",
            )
            fig.update_layout(
                height=335,
                margin=dict(l=0, r=0, t=38, b=0),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.01,
                    xanchor="center",
                    x=.5,
                    font=dict(size=9),
                    itemwidth=30,
                    title=None,
                ),
                annotations=[
                    dict(
                        text=f"<b>{len(andamento)}</b><br><span style='font-size:10px'>processos</span>",
                        x=.5,
                        y=.5,
                        font_size=21,
                        showarrow=False,
                        font=dict(color="#17324d"),
                    )
                ],
            )
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False},
                key="overview_stage_chart",
            )

    with dashboard_right:
        st.markdown(
            '<div class="section-title">Apostilamentos Próximos</div>',
            unsafe_allow_html=True,
        )
        display_overview_table(ap)

        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="section-title">Contratos Próximos do Vencimento</div>',
            unsafe_allow_html=True,
        )
        display_overview_table(urgent)

elif page == "Contratos":
    page_header("Contratos")
    t1, t2, t3, t4 = st.tabs(["A vencer", "Apostilamentos", "Vencidos", "Todos"])
    with t1:
        days = st.slider("Prazo máximo em dias", 1, 180, 90)
        mask = (contrato_dias >= 0) & (contrato_dias <= days)
        view = contratos.loc[aligned_mask(contratos, mask)].copy()
        selected = [c for c in [c_fiscal, c_objeto, c_status, c_contrato_dias] if c and c in view.columns]
        view = view[selected].copy() if selected else view
        rename = {}
        if c_fiscal in view.columns: rename[c_fiscal] = "FISCAL DE CONTRATO"
        if c_objeto in view.columns: rename[c_objeto] = "OBJETO"
        if c_status in view.columns: rename[c_status] = "Status"
        if c_contrato_dias in view.columns: rename[c_contrato_dias] = "DIAS PARA VENCER"
        view = view.rename(columns=rename)
        if "DIAS PARA VENCER" in view:
            view["DIAS PARA VENCER"] = numeric(view["DIAS PARA VENCER"])
            view = view.sort_values("DIAS PARA VENCER")
        pdf_download_button(
            view,
            "Contratos a vencer",
            "contratos_a_vencer.pdf",
            "pdf_contratos_a_vencer",
        )
        display_table(
            view,
            500,
            dynamic_height=True,
            column_widths={
                "FISCAL DE CONTRATO": 180,
                "OBJETO": 500,
                "Status": 120,
                "DIAS PARA VENCER": 105,
            },
            font_size=11,
            responsive_max_height=720,
        )
    with t2:
        days = st.slider("Prazo do apostilamento", 1, 120, 60)
        # Inclui também apostilamentos vencidos, representados por dias negativos.
        mask = apost_dias <= days
        view = contratos.loc[aligned_mask(contratos, mask)].copy()
        selected = [c for c in [c_empresa, c_objeto, c_apost_dias] if c and c in view.columns]
        view = view[selected].copy() if selected else view
        rename = {}
        if c_empresa in view.columns: rename[c_empresa] = "EMPRESA"
        if c_objeto in view.columns: rename[c_objeto] = "OBJETO"
        if c_apost_dias in view.columns: rename[c_apost_dias] = "Dias a Vencer"
        view = view.rename(columns=rename)
        if "Dias a Vencer" in view:
            view["Dias a Vencer"] = numeric(view["Dias a Vencer"])
            view = view.sort_values("Dias a Vencer")
        pdf_download_button(
            view,
            "Apostilamentos",
            "apostilamentos.pdf",
            "pdf_apostilamentos",
        )
        display_table(
            view,
            500,
            dynamic_height=True,
            column_widths={
                "EMPRESA": 230,
                "OBJETO": 600,
                "Dias a Vencer": 110,
            },
            font_size=11,
            responsive_max_height=720,
        )
    with t3:
        expired = contratos.loc[aligned_mask(contratos, contrato_dias < 0)].copy()
        selected = [c for c in [c_objeto, c_status, c_contrato_dias] if c and c in expired.columns]
        expired = expired[selected].copy() if selected else expired
        rename = {}
        if c_objeto in expired.columns: rename[c_objeto] = "OBJETO"
        if c_contrato_dias in expired.columns: rename[c_contrato_dias] = "DIAS VENCIDOS"
        if c_status in expired.columns: rename[c_status] = "Status"
        expired = expired.rename(columns=rename)
        if "DIAS VENCIDOS" in expired:
            expired["DIAS VENCIDOS"] = numeric(expired["DIAS VENCIDOS"]).abs()
            expired = expired.sort_values("DIAS VENCIDOS", ascending=False)
        expired_order = [c for c in ["OBJETO", "Status", "DIAS VENCIDOS"] if c in expired.columns]
        if expired_order:
            expired = expired[expired_order]
        st.error(f"{len(expired)} contrato(s) vencido(s) identificado(s).")
        pdf_download_button(
            expired,
            "Contratos vencidos",
            "contratos_vencidos.pdf",
            "pdf_contratos_vencidos",
        )
        display_table(
            expired,
            500,
            dynamic_height=True,
            column_widths={
                "OBJETO": 700,
                "Status": 140,
                "DIAS VENCIDOS": 110,
            },
            font_size=11,
            responsive_max_height=720,
        )
    with t4:
        search = st.text_input("Pesquisar empresa ou objeto")
        view = contratos.copy()
        if search:
            mask = contains_filter(view, c_empresa, search) | contains_filter(view, c_objeto, search)
            view = view.loc[mask]

        view = format_contract_columns_br(view)

        todos_widths: dict[str, str | int] = {
            column: 105 for column in view.columns
        }
        if c_objeto and c_objeto in view.columns:
            todos_widths[c_objeto] = 250
        if c_empresa and c_empresa in view.columns:
            todos_widths[c_empresa] = 170
        if c_fiscal and c_fiscal in view.columns:
            todos_widths[c_fiscal] = 145

        for column in view.columns:
            normalized = norm(column)
            if "DATA" in normalized or "VIGENCIA" in normalized or "APOSTILAMENTO" in normalized:
                todos_widths[column] = 105
            elif any(term in normalized for term in ["VALOR", "PRECO", "PREÇO", "CUSTO"]):
                todos_widths[column] = 115
            elif "DIA" in normalized:
                todos_widths[column] = 90

        pdf_download_button(
            view,
            "Todos os contratos",
            "todos_os_contratos.pdf",
            "pdf_todos_contratos",
        )

        # Quatro linhas a menos para evitar rolagem vertical externa da página.
        display_table(
            view,
            368,
            dynamic_height=False,
            column_widths=todos_widths,
            font_size=10,
            responsive_max_height=720,
        )

elif page == "Processos concluídos":
    page_header("Processos concluídos", "")
    p_ano = find_col(concluidos, ["ANO"], 1)
    p_tipo = find_col(concluidos, ["TIPO"], 3)
    p_objeto = find_col(concluidos, ["OBJETO"], 6)
    p_solic = find_col(concluidos, ["SOLICITANTE"], 7)
    p_dias = find_col(concluidos, ["DIAS"], 8)
    with st.container(key="filtros_concluidos_mobile"):
        f1, f2, f3, f4 = st.columns(
            [0.8, 1.15, 1.2, 1.7],
            gap="small",
        )
        with f1:
            ano = st.selectbox(
                "Ano",
                ["Todos"] + safe_values(concluidos, p_ano),
            )
        with f2:
            tipo = st.selectbox(
                "Tipo",
                ["Todos"] + safe_values(concluidos, p_tipo),
            )
        with f3:
            solicitante = st.selectbox(
                "Solicitante",
                ["Todos"] + safe_values(concluidos, p_solic),
            )
        with f4:
            objeto = st.text_input("Pesquisar no objeto")
    mask = pd.Series(True, index=concluidos.index)
    if ano != "Todos" and p_ano: mask &= concluidos[p_ano].astype(str) == ano
    if tipo != "Todos" and p_tipo: mask &= concluidos[p_tipo].astype(str) == tipo
    if solicitante != "Todos" and p_solic: mask &= concluidos[p_solic].astype(str) == solicitante
    mask &= contains_filter(concluidos, p_objeto, objeto)
    view = concluidos.loc[mask].copy()
    responsavel = find_col(view, ["RESPONSÁVEL", "RESPONSAVEL"])
    if responsavel in view.columns: view = view.drop(columns=[responsavel])
    with st.container(key="counter_pdf_concluidos"):
        counter_col, pdf_col = st.columns(
            [0.34, 0.16],
            gap="small",
            vertical_alignment="center",
        )
        with counter_col:
            st.markdown(
                f'<div class="results-inline"><span>Resultados encontrados:</span>'
                f'<strong>{len(view)}</strong></div>',
                unsafe_allow_html=True,
            )
        with pdf_col:
            pdf_download_button(
                view,
                "Processos concluídos",
                "processos_concluidos.pdf",
                "pdf_processos_concluidos",
            )
    concluded_widths: dict[str, str | int] = {
        column: 105 for column in view.columns
    }
    if p_objeto and p_objeto in view.columns:
        concluded_widths[p_objeto] = 360
    if p_solic and p_solic in view.columns:
        concluded_widths[p_solic] = 150
    if p_tipo and p_tipo in view.columns:
        concluded_widths[p_tipo] = 135
    if p_ano and p_ano in view.columns:
        concluded_widths[p_ano] = 75
    if p_dias and p_dias in view.columns:
        concluded_widths[p_dias] = 85

    display_table(
        view,
        650,
        dynamic_height=False,
        column_widths=concluded_widths,
        font_size=10,
        responsive_bottom_margin=14,
        responsive_min_height=230,
        responsive_max_height=760,
    )

elif page == "Em andamento":
    page_header("Contratações em andamento", "")
    a_resp = find_col(andamento, ["RESPONSÁVEL", "RESPONSAVEL"], 1)
    a_obj = find_col(andamento, ["OBJETO"], 3)
    a_sol = find_col(andamento, ["SOLICITANTE"], 5)

    # Os quatro filtros ocupam uma linha. O contador fica abaixo deles,
    # usando o mesmo padrão compacto de Processos concluídos.
    with st.container(key="filtros_andamento_mobile"):
        f1, f2, f3, f4 = st.columns(
            [1.15, 1.0, 1.15, 1.55],
            gap="small",
        )
        with f1:
            resp = st.selectbox(
                "Responsável",
                ["Todos"] + safe_values(andamento, a_resp),
            )
        with f2:
            status = st.selectbox(
                "Onde está?",
                ["Todos"] + safe_values(andamento, "STATUS"),
            )
        with f3:
            sol = st.selectbox(
                "Solicitante",
                ["Todos"] + safe_values(andamento, a_sol),
            )
        with f4:
            obj = st.text_input("Pesquisar no objeto")

    mask = pd.Series(True, index=andamento.index)
    if resp != "Todos" and a_resp:
        mask &= andamento[a_resp].astype(str) == resp
    if status != "Todos":
        mask &= andamento["STATUS"] == status
    if sol != "Todos" and a_sol:
        mask &= andamento[a_sol].astype(str) == sol
    mask &= contains_filter(andamento, a_obj, obj)
    view = andamento.loc[mask].copy()

    # Ordem inicial definida para o fluxo do processo.
    status_order = {
        "AGUARDANDO": 0,
        "PLANEJAMENTO": 1,
        "LICITACAO": 2,
        "GESTAO CONTRATO": 3,
        "SEM STATUS": 4,
    }
    if "STATUS" in view.columns:
        view["_ORDEM_STATUS"] = (
            view["STATUS"].map(lambda value: status_order.get(norm(value), 99))
        )
        view = view.sort_values(
            ["_ORDEM_STATUS"],
            kind="stable",
        ).drop(columns=["_ORDEM_STATUS"])

    preferred = [
        a_resp,
        find_col(view, ["MOD", "MODALIDADE"], 2),
        a_obj,
        "STATUS",
        "INFORMAÇÃO / ANDAMENTO",
        a_sol,
        find_col(view, ["DIAS"], 10),
    ]
    preferred = [c for c in preferred if c and c in view.columns]
    table_view = view[preferred].copy() if preferred else view.copy()
    if "STATUS" in table_view.columns:
        table_view = table_view.rename(columns={"STATUS": "Onde está?"})
    andamento_widths: dict[str, str | int] = {
        column: 105 for column in table_view.columns
    }
    if a_resp and a_resp in table_view.columns:
        andamento_widths[a_resp] = 145
    modalidade_col = find_col(table_view, ["MOD", "MODALIDADE"])
    if modalidade_col and modalidade_col in table_view.columns:
        andamento_widths[modalidade_col] = 115
    if a_obj and a_obj in table_view.columns:
        andamento_widths[a_obj] = 270
    if "Onde está?" in table_view.columns:
        andamento_widths["Onde está?"] = 115
    if "INFORMAÇÃO / ANDAMENTO" in table_view.columns:
        andamento_widths["INFORMAÇÃO / ANDAMENTO"] = 250
    if a_sol and a_sol in table_view.columns:
        andamento_widths[a_sol] = 145
    dias_col = find_col(table_view, ["DIAS"])
    if dias_col and dias_col in table_view.columns:
        andamento_widths[dias_col] = 75

    with st.container(key="counter_pdf_andamento"):
        counter_col, pdf_col = st.columns(
            [0.34, 0.16],
            gap="small",
            vertical_alignment="center",
        )
        with counter_col:
            st.markdown(
                f'<div class="results-inline"><span>Processos ativos:</span>'
                f'<strong>{len(view)}</strong></div>',
                unsafe_allow_html=True,
            )
        with pdf_col:
            pdf_download_button(
                table_view,
                "Processos em andamento",
                "processos_em_andamento.pdf",
                "pdf_processos_em_andamento",
            )

    # Aproximadamente cinco linhas a menos para não gerar rolagem externa vertical.
    display_table(
        table_view,
        380,
        dynamic_height=False,
        column_widths=andamento_widths,
        font_size=10,
    )
