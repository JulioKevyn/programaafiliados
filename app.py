import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==============================================================================
# ⚙️ CONFIGURAÇÃO E CSS (NEON GLASS ULTRA)
# ==============================================================================
st.set_page_config(page_title="Nexus Pro Manager", page_icon="📺", layout="wide")

st.markdown("""
<style>
    /* Reset e Fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    .stApp { 
        background-color: #050505; 
        color: #E0E0E0; 
        font-family: 'Inter', sans-serif;
        background-image: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #050505 60%);
    }
    
    /* KPI Cards Futuristas */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(20px);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover { 
        transform: translateY(-5px); 
        border-color: rgba(0, 255, 163, 0.3);
        box-shadow: 0 10px 30px -10px rgba(0, 255, 163, 0.15); 
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; width: 100%; height: 4px;
        background: linear-gradient(90deg, #00FFA3, #00C885);
        opacity: 0.5;
    }
    .metric-title { font-size: 13px; color: #8899A6; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; font-weight: 600; }
    .metric-value { font-size: 32px; font-weight: 800; color: #FFF; letter-spacing: -1px; }
    .metric-sub { font-size: 12px; color: #666; margin-top: 4px; }
    
    /* Cores de Status */
    .status-active { color: #00FFA3; font-weight: bold; }
    .status-warning { color: #FFD700; font-weight: bold; }
    .status-danger { color: #FF4B4B; font-weight: bold; }

    /* Inputs Modernos */
    .stTextInput input, .stNumberInput input, .stSelectbox, .stDateInput input, .stTextArea textarea {
        background-color: #0F0F12 !important; 
        border: 1px solid #2A2A35 !important; 
        color: white !important; 
        border-radius: 8px;
        transition: border 0.3s;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #00FFA3 !important;
    }
    
    /* Tabelas */
    .stDataFrame { border: 1px solid #2A2A35; border-radius: 12px; overflow: hidden; }
    
    /* Botões Neon */
    .stButton button {
        background: linear-gradient(135deg, #00FFA3 0%, #00C885 100%);
        color: #000;
        border: none;
        font-weight: 800;
        letter-spacing: 0.5px;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 255, 163, 0.2);
    }
    .stButton button:hover { 
        transform: scale(1.02); 
        box-shadow: 0 6px 20px rgba(0, 255, 163, 0.4); 
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { 
        background-color: rgba(255,255,255,0.03); 
        border-radius: 12px; 
        padding: 4px; 
        gap: 4px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #1A1A22 !important; 
        color: #00FFA3 !important; 
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 CONEXÃO E UTILS
# ==============================================================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if not url or not key: return None
        return create_client(url, key)
    except: return None

supabase = init_connection()

def get_data(table, order_col='created_at'):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").order(order_col, desc=True).execute()
        df = pd.DataFrame(res.data)
        # Conversão de datas
        cols_date = ['created_at', 'data_expiracao']
        for col in cols_date:
            if not df.empty and col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        # Ajuste fuso horário apenas no created_at
        if not df.empty and 'created_at' in df.columns:
             df['created_at'] = df['created_at'] - timedelta(hours=3)
        return df
    except Exception: return pd.DataFrame()

def render_metric(title, value, sub="", color="#00FFA3"):
    st.markdown(f"""
    <div class="metric-card" style="border-top-color: {color};">
        <div class="metric-title" style="color: {color}">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

def calcular_status_tempo(data_exp):
    if pd.isnull(data_exp): return "Sem Data", "grey"
    hoje = datetime.now()
    delta = (data_exp - hoje).days
    
    if delta < 0: return "VENCIDO", "#FF4B4B" # Vermelho
    if delta <= 3: return f"VENCE EM {delta} DIAS", "#FFD700" # Amarelo
    return "ATIVO", "#00FFA3" # Verde

# ==============================================================================
# 🔐 LOGIN
# ==============================================================================
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'role': None, 'user': {}})

def login_ui():
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 3rem;'>NEXUS <span style='color:#00FFA3'>PRO</span></h1>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Parceiro", "Administrador"])
        
        with tab1:
            with st.container(border=True):
                cupom = st.text_input("Seu Código (Cupom)").strip().upper()
                if st.button("Acessar Painel Parceiro", use_container_width=True):
                    if not supabase: st.error("Erro de Conexão"); return
                    res = supabase.table("afiliados").select("*").eq("cupom", cupom).execute()
                    if res.data:
                        st.session_state.update({'logged_in': True, 'role': 'afiliado', 'user': res.data[0]})
                        st.rerun()
                    else: st.error("Código inválido.")
        
        with tab2:
            with st.container(border=True):
                senha = st.text_input("Chave de Acesso", type="password")
                if st.button("Acessar Admin", use_container_width=True):
                    if senha == st.secrets.get("ADMIN_PASSWORD", "admin123"):
                        st.session_state.update({'logged_in': True, 'role': 'admin'})
                        st.rerun()
                    else: st.error("Acesso negado.")

# ==============================================================================
# 🛡️ DASHBOARD ADMIN (SUPER COMPLETO)
# ==============================================================================
def admin_dash():
    with st.sidebar:
        st.markdown("### 🛡️ NEXUS ADMIN")
        menu = st.radio("", ["Dashboard", "Vendas & Clientes", "Planos & Config", "Afiliados", "Marketing", "Financeiro"])
        st.divider()
        if st.button("Sair do Sistema"):
            st.session_state.clear()
            st.rerun()

    # Cache Data
    df_vendas = get_data('vendas')
    df_afiliados = get_data('afiliados')
    df_planos = get_data('planos', 'valor')
    df_saques = get_data('saques')

    # 1. VISÃO GERAL -----------------------------------------------------------
    if menu == "Dashboard":
        st.markdown("## 📊 Visão Geral da Operação")
        
        # Filtros de Data
        col_d1, col_d2 = st.columns([4, 1])
        with col_d2:
            periodo = st.selectbox("Período", ["7 Dias", "30 Dias", "Este Mês", "Total"], index=1)
        
        # Lógica de Filtro
        if not df_vendas.empty:
            hoje = datetime.now()
            if periodo == "7 Dias": data_corte = hoje - timedelta(days=7)
            elif periodo == "30 Dias": data_corte = hoje - timedelta(days=30)
            elif periodo == "Este Mês": data_corte = hoje.replace(day=1)
            else: data_corte = hoje - timedelta(days=3650)
            
            df_filt = df_vendas[df_vendas['created_at'] >= data_corte]
            
            # Métricas Calculadas
            vendas_totais = len(df_filt)
            faturamento = df_filt['valor_plano'].sum()
            lucro = faturamento - df_filt['valor_comissao'].sum()
            ticket_medio = faturamento / vendas_totais if vendas_totais > 0 else 0
            
            # Vencendo em breve (Global)
            vencendo = 0
            if 'data_expiracao' in df_vendas.columns:
                mask_vence = (df_vendas['data_expiracao'] <= (hoje + timedelta(days=3))) & (df_vendas['data_expiracao'] >= hoje)
                vencendo = len(df_vendas[mask_vence])
            
            # KPIs
            k1, k2, k3, k4 = st.columns(4)
            with k1: render_metric("Vendas no Período", vendas_totais, "Novas assinaturas")
            with k2: render_metric("Faturamento", f"R$ {faturamento:,.2f}", "Bruto gerado")
            with k3: render_metric("Lucro Líquido", f"R$ {lucro:,.2f}", "Após comissões", "#00E0FF")
            with k4: render_metric("Renovações Pendentes", vencendo, "Vencem em 3 dias", "#FFD700" if vencendo > 0 else "#00FFA3")
            
            st.markdown("---")
            
            # Gráficos
            g1, g2 = st.columns([2, 1])
            with g1:
                st.subheader("📈 Fluxo de Caixa Diário")
                if not df_filt.empty:
                    daily = df_filt.groupby(df_filt['created_at'].dt.date)[['valor_plano']].sum().reset_index()
                    fig = px.bar(daily, x='created_at', y='valor_plano', template="plotly_dark")
                    fig.update_traces(marker_color='#00FFA3', marker_line_width=0)
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig, use_container_width=True)
            
            with g2:
                st.subheader("🏆 Top Planos")
                if not df_filt.empty and 'plano_nome' in df_filt.columns:
                    top_planos = df_filt['plano_nome'].value_counts().reset_index()
                    fig2 = px.pie(top_planos, values='count', names='plano_nome', hole=0.7, color_discrete_sequence=px.colors.sequential.Tealgrn_r)
                    fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=False, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sem dados de vendas para exibir.")

    # 2. VENDAS E CLIENTES -----------------------------------------------------
    elif menu == "Vendas & Clientes":
        st.markdown("## 📋 Gestão de Clientes")
        
        # Tabs internas
        tab_nova, tab_lista = st.tabs(["➕ Nova Assinatura", "🔍 Base de Clientes"])
        
        with tab_nova:
            with st.container(border=True):
                st.markdown("### Registrar Venda Manual")
                with st.form("form_venda_admin"):
                    c1, c2 = st.columns(2)
                    nome_cliente = c1.text_input("Nome do Cliente", placeholder="Ex: João da Silva")
                    whatsapp_cliente = c2.text_input("WhatsApp do Cliente", placeholder="5511999999999")
                    
                    c3, c4 = st.columns(2)
                    # Selectbox de Planos dinâmico
                    opcoes_planos = {f"{row['nome']} (R$ {row['valor']})": row for i, row in df_planos.iterrows()} if not df_planos.empty else {}
                    plano_selecionado = c3.selectbox("Selecione o Plano", list(opcoes_planos.keys()) if opcoes_planos else ["Padrão - R$ 35.00"])
                    
                    cupom_parceiro = c4.text_input("Cupom Parceiro (Opcional)").upper()
                    
                    if st.form_submit_button("✅ Confirmar Venda"):
                        if opcoes_planos:
                            dados_plano = opcoes_planos[plano_selecionado]
                            valor_final = float(dados_plano['valor'])
                            dias_plano = int(dados_plano['dias'])
                            nome_plano = dados_plano['nome']
                            # Verifica comissão do plano ou usa a fixa do parceiro
                            comissao = float(dados_plano['comissao_fixa'])
                        else:
                            valor_final = 35.0
                            dias_plano = 30
                            nome_plano = "Manual"
                            comissao = 0.0

                        # Se tiver cupom, valida parceiro e sobrescreve comissão se necessário
                        if cupom_parceiro:
                            check = supabase.table("afiliados").select("*").eq("cupom", cupom_parceiro).execute()
                            if check.data:
                                # Se o plano não tem comissão fixa definida (0), usa padrão R$ 15,00 ou lógica custom
                                if comissao == 0: comissao = 15.00 
                            else:
                                st.warning("Cupom não existe! Venda registrada sem comissão.")
                                cupom_parceiro = None
                                comissao = 0

                        # Data Expiração
                        data_exp = datetime.now() + timedelta(days=dias_plano)
                        
                        supabase.table("vendas").insert({
                            "nome_cliente": nome_cliente,
                            "valor_plano": valor_final,
                            "cupom": cupom_parceiro,
                            "valor_comissao": comissao,
                            "plano_nome": nome_plano,
                            "data_expiracao": data_exp.strftime('%Y-%m-%d'),
                            "status": "Ativo"
                        }).execute()
                        st.toast("Venda registrada com sucesso!", icon="✅")
                        time.sleep(1)
                        st.rerun()

        with tab_lista:
            if not df_vendas.empty:
                # Busca rápida
                search = st.text_input("Buscar Cliente (Nome)", placeholder="Digite para filtrar...")
                df_show = df_vendas[df_vendas['nome_cliente'].str.contains(search, case=False, na=False)] if search else df_vendas
                
                # Lista customizada com HTML
                st.markdown("### Lista de Clientes")
                for i, row in df_show.iterrows():
                    # Lógica de status
                    status_txt, status_cor = calcular_status_tempo(row['data_expiracao']) if 'data_expiracao' in row else ("N/A", "grey")
                    
                    with st.expander(f"{status_txt} | {row['nome_cliente']} ({row['plano_nome'] if 'plano_nome' in row else 'N/A'})"):
                        c_info, c_action = st.columns([3, 1])
                        with c_info:
                            st.write(f"**Data Venda:** {row['created_at'].strftime('%d/%m/%Y') if not pd.isnull(row['created_at']) else '-'}")
                            st.write(f"**Vencimento:** {row['data_expiracao'].strftime('%d/%m/%Y') if 'data_expiracao' in row and not pd.isnull(row['data_expiracao']) else '-'}")
                            st.write(f"**Valor:** R$ {row['valor_plano']} | **Comissão:** R$ {row['valor_comissao']}")
                            st.write(f"**Cupom:** {row['cupom'] if row['cupom'] else 'Direta'}")
                        
                        with c_action:
                            st.markdown("#### Ações")
                            # Botão Renovar
                            if st.button("🔄 Renovar 30 Dias", key=f"renov_{row['id']}"):
                                nova_exp = (row['data_expiracao'] if not pd.isnull(row['data_expiracao']) else datetime.now()) + timedelta(days=30)
                                supabase.table("vendas").update({"data_expiracao": nova_exp.strftime('%Y-%m-%d'), "status": "Ativo"}).eq("id", row['id']).execute()
                                st.success("Renovado!")
                                time.sleep(0.5)
                                st.rerun()
                            
                            # Botão Cancelar
                            if st.button("❌ Cancelar", key=f"canc_{row['id']}"):
                                supabase.table("vendas").update({"status": "Cancelado"}).eq("id", row['id']).execute()
                                st.rerun()
                            
                            # Link WhatsApp Cobrança
                            msg = f"Olá {row['nome_cliente']}, seu plano Nexus TV vence dia {row['data_expiracao'].strftime('%d/%m')}. Vamos renovar?"
                            link = f"https://wa.me/?text={msg.replace(' ', '%20')}"
                            st.link_button("💬 Cobrar no Zap", link)
            else:
                st.info("Nenhuma venda encontrada.")

    # 3. PLANOS E CONFIG -------------------------------------------------------
    elif menu == "Planos & Config":
        st.markdown("## 🛠️ Configuração de Planos")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### Novo Plano")
            with st.form("add_plan"):
                nome_p = st.text_input("Nome (Ex: Mensal 4K)")
                valor_p = st.number_input("Valor Venda (R$)", value=35.0)
                dias_p = st.number_input("Duração (Dias)", value=30)
                comissao_p = st.number_input("Comissão Fixa Parceiro", value=15.0)
                if st.form_submit_button("Salvar Plano"):
                    supabase.table("planos").insert({
                        "nome": nome_p, "valor": valor_p, "dias": dias_p, "comissao_fixa": comissao_p
                    }).execute()
                    st.success("Plano criado!")
                    time.sleep(1)
                    st.rerun()
        
        with c2:
            st.markdown("### Planos Ativos")
            if not df_planos.empty:
                st.dataframe(
                    df_planos[['nome', 'valor', 'dias', 'comissao_fixa']], 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "valor": st.column_config.NumberColumn("Preço", format="R$ %.2f"),
                        "comissao_fixa": st.column_config.NumberColumn("Comissão", format="R$ %.2f")
                    }
                )
                # Botão para deletar (simplificado via ID se necessário)
                id_del = st.number_input("ID para Deletar", min_value=0)
                if st.button("Deletar Plano por ID") and id_del > 0:
                     supabase.table("planos").delete().eq("id", id_del).execute()
                     st.rerun()

    # 4. AFILIADOS -------------------------------------------------------------
    elif menu == "Afiliados":
        st.markdown("## 👥 Gestão de Parceiros")
        
        with st.expander("➕ Cadastrar Novo Parceiro"):
            with st.form("new_aff"):
                ca1, ca2 = st.columns(2)
                nome_a = ca1.text_input("Nome Completo")
                cupom_a = ca2.text_input("CUPOM EXCLUSIVO").upper()
                whats_a = st.text_input("WhatsApp")
                if st.form_submit_button("Cadastrar"):
                    try:
                        supabase.table("afiliados").insert({"nome": nome_a, "cupom": cupom_a, "whatsapp": whats_a}).execute()
                        st.success("Parceiro cadastrado!")
                        st.rerun()
                    except: st.error("Erro: Cupom já existe.")

        if not df_afiliados.empty:
            st.dataframe(df_afiliados, use_container_width=True, hide_index=True)

    # 5. MARKETING -------------------------------------------------------------
    elif menu == "Marketing":
        st.markdown("## 📢 Materiais para Afiliados")
        st.write("Adicione textos e links que aparecerão no painel dos seus parceiros.")
        
        with st.form("mkt_form"):
            titulo_m = st.text_input("Título do Material")
            tipo_m = st.selectbox("Tipo", ["Texto (Copy)", "Link Imagem (Banner)"])
            conteudo_m = st.text_area("Conteúdo (Texto ou URL)")
            if st.form_submit_button("Publicar Material"):
                supabase.table("marketing").insert({"titulo": titulo_m, "tipo": tipo_m, "conteudo": conteudo_m}).execute()
                st.success("Publicado!")

    # 6. FINANCEIRO ------------------------------------------------------------
    elif menu == "Financeiro":
        st.markdown("## 💰 Solicitações de Saque")
        
        if not df_saques.empty:
            pendentes = df_saques[df_saques['status'] == 'Pendente']
            historico = df_saques[df_saques['status'] != 'Pendente']
            
            if not pendentes.empty:
                st.error(f"🔔 Existem {len(pendentes)} solicitações pendentes!")
                for i, row in pendentes.iterrows():
                    with st.container(border=True):
                        cols = st.columns([2, 1, 1, 1])
                        cols[0].write(f"**{row['cupom']}** pediu **R$ {row['valor']:.2f}**")
                        cols[1].caption(row['created_at'].strftime('%d/%m %H:%M'))
                        if cols[2].button("✅ Pagar", key=f"pay_{row['id']}"):
                            supabase.table("saques").update({"status": "Pago"}).eq("id", row['id']).execute()
                            st.rerun()
                        if cols[3].button("🚫 Negar", key=f"deny_{row['id']}"):
                            supabase.table("saques").update({"status": "Rejeitado"}).eq("id", row['id']).execute()
                            st.rerun()
            else:
                st.success("Tudo em dia! Sem pendências.")
            
            st.markdown("### Histórico")
            st.dataframe(historico, use_container_width=True, hide_index=True)

# ==============================================================================
# 🚀 DASHBOARD PARCEIRO
# ==============================================================================
def affiliate_dash():
    user = st.session_state['user']
    cupom = user['cupom']
    
    with st.sidebar:
        st.markdown(f"# 👋 Olá, {user['nome'].split()[0]}")
        st.markdown(f"""
        <div style="background:#1A1A22; padding:10px; border-radius:8px; border:1px solid #333; text-align:center;">
            <small>SEU CUPOM</small><br>
            <strong style="font-size:1.5rem; color:#00FFA3">{cupom}</strong>
        </div>
        """, unsafe_allow_html=True)
        
        menu = st.radio("Menu", ["Resumo", "Meus Clientes", "Marketing", "Financeiro"])
        st.divider()
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

    df_vendas = get_data('vendas')
    minhas_vendas = df_vendas[df_vendas['cupom'] == cupom] if not df_vendas.empty else pd.DataFrame()

    # 1. RESUMO ----------------------------------------------------------------
    if menu == "Resumo":
        st.markdown("## 🚀 Performance")
        
        # Cálculos
        ativas = minhas_vendas[minhas_vendas['status'] == 'Ativo'] if not minhas_vendas.empty else pd.DataFrame()
        total_comissao = ativas['valor_comissao'].sum() if not ativas.empty else 0
        
        df_saques = get_data('saques')
        meus_saques = df_saques[(df_saques['cupom'] == cupom) & (df_saques['status'] != 'Rejeitado')] if not df_saques.empty else pd.DataFrame()
        sacado = meus_saques['valor'].sum() if not meus_saques.empty else 0
        disponivel = total_comissao - sacado

        c1, c2, c3 = st.columns(3)
        with c1: render_metric("Clientes Ativos", len(ativas), "Recorrência garantida")
        with c2: render_metric("Saldo Total", f"R$ {total_comissao:.2f}", "Acumulado")
        with c3: render_metric("Disponível Saque", f"R$ {disponivel:.2f}", "Solicite no menu Financeiro", "#D300C5")

        st.markdown("### ⚡ Links Rápidos")
        c_link, c_copia = st.columns([3, 1])
        with c_link:
            msg = f"Olá! Quero assinar o Nexus TV com o cupom {cupom}."
            link_zap = f"https://wa.me/5511999999999?text={msg.replace(' ', '%20')}"
            st.code(link_zap, language="text")
        with c_copia:
            st.info("👆 Copie e mande para seu cliente.")

    # 2. MEUS CLIENTES ---------------------------------------------------------
    elif menu == "Meus Clientes":
        st.markdown("## 🤝 Sua Carteira de Clientes")
        
        if not minhas_vendas.empty:
            for i, row in minhas_vendas.iterrows():
                status_txt, status_cor = calcular_status_tempo(row['data_expiracao']) if 'data_expiracao' in row else ("-", "grey")
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.write(f"**{row['nome_cliente']}**")
                    c1.caption(f"Plano: {row.get('plano_nome', 'Padrão')}")
                    
                    c2.markdown(f"<span style='color:{status_cor}'>{status_txt}</span>", unsafe_allow_html=True)
                    if 'data_expiracao' in row and not pd.isnull(row['data_expiracao']):
                         c2.caption(f"Vence: {row['data_expiracao'].strftime('%d/%m')}")
                    
                    # Botão cobrar
                    msg = f"Oi {row['nome_cliente']}! Seu plano vence dia {row['data_expiracao'].strftime('%d/%m')}. Vamos renovar?"
                    link = f"https://wa.me/?text={msg.replace(' ', '%20')}"
                    c3.link_button("📲 Cobrar", link, use_container_width=True)
        else:
            st.info("Você ainda não tem vendas.")

    # 3. MARKETING -------------------------------------------------------------
    elif menu == "Marketing":
        st.markdown("## 📢 Materiais de Divulgação")
        df_mkt = get_data("marketing")
        
        if not df_mkt.empty:
            for i, row in df_mkt.iterrows():
                with st.expander(f"📌 {row['titulo']}"):
                    if row['tipo'] == "Texto (Copy)":
                        st.code(row['conteudo'], language="text")
                    else:
                        st.image(row['conteudo'])
                        st.caption(row['conteudo'])
        else:
            st.info("O Admin ainda não postou materiais.")

    # 4. FINANCEIRO ------------------------------------------------------------
    elif menu == "Financeiro":
        st.markdown("## 💸 Seus Ganhos")
        
        # Recalcular saldo
        ativas = minhas_vendas[minhas_vendas['status'] == 'Ativo'] if not minhas_vendas.empty else pd.DataFrame()
        total_comissao = ativas['valor_comissao'].sum() if not ativas.empty else 0
        df_saques = get_data('saques')
        meus_saques = df_saques[(df_saques['cupom'] == cupom) & (df_saques['status'] != 'Rejeitado')] if not df_saques.empty else pd.DataFrame()
        sacado = meus_saques['valor'].sum() if not meus_saques.empty else 0
        disponivel = total_comissao - sacado
        
        st.metric("Disponível para Saque", f"R$ {disponivel:.2f}")
        
        with st.form("solicitar_saque"):
            valor = st.number_input("Valor do Saque (R$)", min_value=10.0, max_value=float(disponivel) if disponivel > 0 else 10.0)
            pix = st.text_input("Sua Chave PIX")
            if st.form_submit_button("Solicitar Pix") and disponivel >= valor:
                supabase.table("saques").insert({"cupom": cupom, "valor": valor, "status": "Pendente", "comprovante": pix}).execute()
                st.success("Solicitação enviada!")
                st.rerun()

        st.markdown("#### Histórico")
        if not meus_saques.empty:
            st.dataframe(meus_saques[['created_at', 'valor', 'status']], use_container_width=True)

# ==============================================================================
# 🚦 ROTEAMENTO
# ==============================================================================
if not st.session_state['logged_in']:
    login_ui()
else:
    if st.session_state['role'] == 'admin':
        admin_dash()
    elif st.session_state['role'] == 'afiliado':
        affiliate_dash()
