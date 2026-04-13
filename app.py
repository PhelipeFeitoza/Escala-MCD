import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gestão Field Service McDonalds", layout="wide")

# 2. FUNÇÃO PARA PROCESSAR O EXCEL
def processar_excel(file):
    df = pd.read_excel(file, engine='openpyxl')
    info_cols = df.iloc[:, [0, 2, 3, 4]].copy()
    info_cols.columns = ['ID', 'Regiao', 'Horario', 'Tecnico']
    
    # Tratamento básico de nomes
    info_cols['Regiao'] = info_cols['Regiao'].astype(str).str.upper()
    info_cols['Tecnico'] = info_cols['Tecnico'].astype(str)
    
    datas_cols = df.iloc[:, 5:]
    df_unido = pd.concat([info_cols, datas_cols], axis=1)
    df_long = df_unido.melt(id_vars=['ID', 'Regiao', 'Horario', 'Tecnico'], var_name='Data_Bruta', value_name='Status')
    df_long['Data'] = pd.to_datetime(df_long['Data_Bruta'], errors='coerce')
    df_long = df_long.dropna(subset=['Data'])
    
    # --- REGRAS DE NEGÓCIO ---
    def mapear_produtividade(row):
        status = str(row['Status']).upper().strip()
        regiao = str(row['Regiao']).upper()
        
        # Categorias
        is_trabalho = status in ['TBC', 'TBM', 'TBA', 'FUP']
        is_abs = status in ['VAGA', 'FT', 'LM', 'FR', 'FALTA', 'FÉRIAS', 'LICENÇA MÉDICA']
        is_neutro = status in ['FG', 'BH', 'TR', 'PV']
        
        # Meta Call Rate
        meta = 0
        if is_trabalho:
            meta = 4 if 'SP' in regiao else 3
            
        return pd.Series([is_trabalho, is_abs, is_neutro, meta])

    df_long[['Trabalho', 'Absenteismo', 'Neutro', 'Meta_CallRate']] = df_long.apply(mapear_produtividade, axis=1)
    return df_long

# 3. INTERFACE
st.sidebar.title("🚀 Sistema Field Service")
arquivo_upload = st.sidebar.file_uploader("Suba a planilha de Escala", type=['xlsx'])

if arquivo_upload is not None:
    df_base = processar_excel(arquivo_upload)
    
    # MENU DE NAVEGAÇÃO
    aba = st.sidebar.radio("Navegar para:", ["📈 Painel de Produtividade", "📅 Escala Mensal", "👤 Área do Técnico"])
    data_sel = st.sidebar.date_input("Selecione o dia de análise:", datetime(2026, 4, 13))

    # --- ABA: PAINEL DE PRODUTIVIDADE (O QUE VOCÊ PEDIU) ---
    if aba == "📈 Painel de Produtividade":
        st.title(f"📊 Dashboard de Produtividade - {data_sel.strftime('%d/%m/%Y')}")
        
        df_dia = df_base[df_base['Data'].dt.date == data_sel]
        
        # 1. MÉTRICAS GERAIS (HEADCOUNT)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_equipe = len(df_dia)
            st.metric("Headcount Total Equipe", total_equipe)
        with col2:
            equipe_ativa = df_dia['Trabalho'].sum()
            st.metric("Headcount Dia Ativo", int(equipe_ativa))
        with col3:
            absenteismo = df_dia['Absenteismo'].sum()
            st.metric("Total Absenteísmo", int(absenteismo), delta=f"{int(absenteismo)} ausentes", delta_color="inverse")
        with col4:
            cap_total = df_dia['Meta_CallRate'].sum()
            st.metric("Produtividade Total (Chamados)", int(cap_total))

        st.divider()

        # 2. DETALHAMENTO POR REGIONAL
        st.subheader("📍 Desempenho por Regional")
        reg_cols = st.columns(4)
        regionais = ["SP", "SUL", "NORDESTE", "INTERIOR"]
        
        for i, reg in enumerate(regionais):
            with reg_cols[i]:
                df_reg = df_dia[df_dia['Regiao'].str.contains(reg)]
                hc_reg = df_reg['Trabalho'].sum()
                call_rate_reg = df_reg['Meta_CallRate'].sum()
                st.info(f"**{reg}**")
                st.write(f"HC Ativo: {int(hc_reg)}")
                st.write(f"Call Rate: {int(call_rate_reg)}")

        st.divider()

        # 3. CONTROLE DE SUB-REGIÕES SP (MÉTRICA COM ÍCONES)
        st.subheader("🔍 Status Sub-regiões (SP)")
        
        # Aqui listamos as sub-regiões baseadas no seu print
        sub_sp = ["SP-CENTRO", "SP-LESTE", "SP-NORTE", "SP-OESTE", "SP-SUL", "SP-ABC"]
        sub_cols = st.columns(len(sub_sp))
        
        for i, sub in enumerate(sub_sp):
            with sub_cols[i]:
                df_sub = df_dia[df_dia['Regiao'].str.contains(sub)]
                hc_sub = int(df_sub['Trabalho'].sum())
                
                # Lógica de ícones (Exemplo: Se HC for 0 é erro, se for menor que a média é alerta)
                if hc_sub >= 3:
                    icon = "✅"
                    cor = "green"
                elif hc_sub > 0:
                    icon = "⚠️"
                    cor = "orange"
                else:
                    icon = "❌"
                    cor = "red"
                
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 10px; border-radius: 5px; text-align: center;">
                    <p style="font-size: 0.8em; margin-bottom: 5px;">{sub}</p>
                    <h2 style="color: {cor};">{hc_sub}</h2>
                    <span>{icon}</span>
                </div>
                """, unsafe_allow_html=True)

    # --- ABA: ESCALA MENSAL ---
    elif aba == "📅 Escala Mensal":
        st.title("Escala Mensal Empilhada")
        mes_sel = st.sidebar.slider("Mês", 1, 12, data_sel.month)
        df_m = df_base[df_base['Data'].dt.month == mes_sel]
        df_pivot = df_m.pivot(index=['ID', 'Regiao', 'Tecnico'], columns='Data', values='Status').sort_index(level='ID')
        st.dataframe(df_pivot, height=600)

    # --- ABA: ÁREA DO TÉCNICO ---
    elif aba == "👤 Área do Técnico":
        st.title("Meu Calendário de Trabalho")
        tec_sel = st.selectbox("Selecione seu nome:", df_base['Tecnico'].unique())
        # (Aqui entra o código do calendário individual que já fizemos)

else:
    st.info("Aguardando upload da planilha ESCALA 2026...")
