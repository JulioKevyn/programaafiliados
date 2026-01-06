import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
from datetime import datetime, timedelta
import time

# ==============================================================================
# ⚙️ CONFIG
# ==============================================================================
st.set_page_config(
    page_title="OLYMPIKUS IPTV",
    page_icon="⚡",
    layout="wide"
)

# ==============================================================================
# 🎨 TEMA PREMIUM
# ==============================================================================
st.markdown("""
<style>
.stApp { background-color:#0B0F1A; color:#E6EDF3; }
header, footer { visibility:hidden; }

h1,h2,h3 { font-weight:700; }

.kpi {
    background:#12182B;
    border-radius:14px;
    padding:22px;
    text-align:center;
    border:1px solid #1F2A44;
}
.kpi-title { color:#8B949E; font-size:12px; text-transform:uppercase; }
.kpi-value { font-size:30px; font-weight:800; margin-top:5px; }

.blue { color:#2F81F7; }
.green { color:#3FB950; }
.gold { color:#F5C542; }

.stButton button {
    background:#2F81F7;
    border:none;
    font-weight:700;
    border-radius:8px;
}
.stButton button:hover { background:#1F6FEB; }

[data-testid="stDataFrame"] {
    border-radius:12px;
    border:1px solid #1F2A44;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 SUPABASE
# ==============================================================================
@st.cache_resource
def init_db():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

db = init_db()

def load(table):
    res = db.table(table).select("*").execute()
    df = pd.DataFrame(res.data)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"]) - timedelta(hours=3)
    return df

# ==============================================================================
# 🔐 LOGIN
# ==============================================================================
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None
    st.session_state.user = None

def login():
    st.markdown("<h1 style='text-align:center'>⚡ OLYMPIKUS IPTV</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#8B949E'>Sistema Profissional de Gestão</p>", unsafe_allow_html=True)
    st.markdown("----")

    tab1, tab2 = st.tabs(["🤝 Afiliado", "🛡 Admin"])

    with tab1:
        cupom = st.text_input("Cupom").upper()
        if st.button("Entrar"):
            r = db.table("afiliados").select("*").eq("cupom", cupom).execute()
            if r.data:
                st.session_state.auth = True
                st.session_state.role = "afiliado"
                st.session_state.user = r.data[0]
                st.rerun()
            else:
                st.error("Cupom inválido")

    with tab2:
        senha = st.text_input("Senha Master", type="password")
        if st.button("Acessar Admin"):
            if senha == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.auth = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Senha incorreta")

# ==============================================================================
# 🛡 ADMIN DASHBOARD
# ==============================================================================
def admin():
    vendas = load("vendas")
    afiliados = load("afiliados")

    ativos = vendas[vendas.status == "Ativo"]
    faturamento = ativos.valor_plano.sum()
    comissoes = ativos.valor_comissao.sum()

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='kpi'><div class='kpi-title'>Vendas</div><div class='kpi-value blue'>{len(vendas)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi'><div class='kpi-title'>Ativos</div><div class='kpi-value green'>{len(ativos)}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi'><div class='kpi-title'>Faturamento</div><div class='kpi-value'>R$ {faturamento:.0f}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi'><div class='kpi-title'>Lucro</div><div class='kpi-value gold'>R$ {faturamento - comissoes:.0f}</div></div>", unsafe_allow_html=True)

    st.markdown("### 📈 Vendas por Dia")
    chart = ativos.groupby(ativos.created_at.dt.date)["valor_plano"].sum().reset_index()
    st.plotly_chart(
        px.line(chart, x="created_at", y="valor_plano", markers=True),
        use_container_width=True
    )

    st.markdown("### 🏆 Ranking Afiliados")
    rank = ativos.groupby("cupom")["valor_comissao"].sum().reset_index().sort_values("valor_comissao", ascending=False)
    st.dataframe(rank, use_container_width=True)

    st.download_button(
        "📥 Exportar Vendas CSV",
        vendas.to_csv(index=False),
        "vendas_olympikus.csv"
    )

    if st.sidebar.button("🚪 Sair"):
        st.session_state.auth = False
        st.rerun()

# ==============================================================================
# 🤝 AFILIADO DASHBOARD
# ==============================================================================
def afiliado():
    user = st.session_state.user
    vendas = load("vendas")
    df = vendas[vendas.cupom == user["cupom"]]

    ativos = df[df.status == "Ativo"]
    saldo = ativos.valor_comissao.sum()

    c1,c2 = st.columns(2)
    c1.markdown(f"<div class='kpi'><div class='kpi-title'>Clientes</div><div class='kpi-value green'>{len(ativos)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi'><div class='kpi-title'>Saldo</div><div class='kpi-value gold'>R$ {saldo:.2f}</div></div>", unsafe_allow_html=True)

    st.markdown("### 📋 Minhas Vendas")
    st.dataframe(df, use_container_width=True)

    if st.sidebar.button("🚪 Sair"):
        st.session_state.auth = False
        st.rerun()

# ==============================================================================
# 🚦 ROUTER
# ==============================================================================
if not st.session_state.auth:
    login()
else:
    if st.session_state.role == "admin":
        admin()
    else:
        afiliado()
