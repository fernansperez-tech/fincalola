import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Finca Lola - 86.1 Ha", page_icon="🍌", layout="centered")

COLORES_CINTA = ["Amarilla", "Morada", "Roja", "Café", "Negra", "Verde", "Azul", "Blanca"]
LOTES = [f"Lote {i:02d}" for i in range(1, 15)]
PARCELEROS_BASE = [
    "Carracedo Daison",
    "Reales Isaac",
    "Chiquillo Libardo",
    "Luis Fernandez",
    "Cantillo Pedro",
    "Andrés López",
    "Miguel Torres",
    "Jorge Ramírez",
    "Roberto Castro",
    "Fernando Ruiz",
    "Evenildo Felipe",
    "Otro (Escribir nombre)"
]
CLAVE_ADMIN = "banano2026"
ID_HOJA = "1WnHs71IMeuz9X9sAtJkNYJbR9QJE2QqAKq37-PGsr-0"
NOMBRE_HOJA = "Hoja 1"

if "cola_offline" not in st.session_state:
    st.session_state.cola_offline = []

def conectar_hoja():
    sec = st.secrets["connections"]["gsheets"]
    llave_privada = sec["private_key"].replace("\\n", "\n")
    prefijo = "https" + chr(58) + "//"
    dominio_g = "googleapis.com"
    info_credenciales = {
        "type": "service_account",
        "project_id": sec["project_id"],
        "private_key_id": sec["private_key_id"],
        "private_key": llave_privada,
        "client_email": sec["client_email"],
        "client_id": sec["client_id"],
        "auth_uri": prefijo + "://google.com",
        "token_uri": prefijo + "oauth2." + dominio_g + "/token",
        "auth_provider_x509_cert_url": prefijo + "www." + dominio_g + "/oauth2/v1/certs",
        "client_x509_cert_url": sec.get("client_x509_cert_url", "")
    }
    alcances = [
        prefijo + "www." + dominio_g + "/auth/spreadsheets",
        prefijo + "www." + dominio_g + "/auth/drive"
    ]
    credenciales = Credentials.from_service_account_info(info_credenciales, scopes=alcances)
    gc = gspread.authorize(credenciales)
    sh = gc.open_by_key(ID_HOJA)
    return sh.worksheet(NOMBRE_HOJA)

def cargar_datos():
    try:
        ws = conectar_hoja()
        datos = ws.get_all_records()
        if not datos:
            return pd.DataFrame(columns=["Fecha", "Hora", "Semana", "Lote", "Parcelero", "Color_Cinta", "Racimos", "Estado"])
        return pd.DataFrame(datos)
    except Exception:
        return pd.DataFrame(columns=["Fecha", "Hora", "Semana", "Lote", "Parcelero", "Color_Cinta", "Racimos", "Estado"])

def agregar_filas(lista_registros):
    ws = conectar_hoja()
    filas = []
    for r in lista_registros:
        filas.append([
            r["Fecha"], r["Hora"], int(r["Semana"]), r["Lote"],
            r["Parcelero"], r["Color_Cinta"], int(r["Racimos"]), r["Estado"]
        ])
    ws.append_rows(filas)

def procesar_csv_tableta(df_tab, col_lote, col_color, col_fecha=None):
    ahora = datetime.now()
    cols_usar = [col_lote, col_color]
    if col_fecha and col_fecha != "Usar fecha de hoy":
        cols_usar.append(col_fecha)
        
    df_limpio = df_tab[cols_usar].dropna().copy()
    if df_limpio.empty:
        return []

    if col_fecha and col_fecha != "Usar fecha de hoy":
        df_limpio["Fecha_Norm"] = pd.to_datetime(df_limpio[col_fecha], errors="coerce").dt.strftime("%Y-%m-%d")
        df_limpio["Fecha_Norm"] = df_limpio["Fecha_Norm"].fillna(ahora.strftime("%Y-%m-%d"))
    else:
        df_limpio["Fecha_Norm"] = ahora.strftime("%Y-%m-%d")

    conteo = df_limpio.groupby(["Fecha_Norm", col_lote, col_color]).size().reset_index(name="Total_Racimos")
    
    descuentos = []
    for _, fila in conteo.iterrows():
        lote_raw = str(fila[col_lote]).strip()
        num_lote = "".join(filter(str.isdigit, lote_raw))
        lote_norm = f"Lote {int(num_lote):02d}" if num_lote else lote_raw
        color_norm = str(fila[col_color]).strip().capitalize()
        cant = int(fila["Total_Racimos"])
        fecha_str = str(fila["Fecha_Norm"])
        try:
            semana_num = datetime.strptime(fecha_str, "%Y-%m-%d").isocalendar().week
        except Exception:
            semana_num = ahora.isocalendar().week
            
        descuentos.append({
            "Fecha": fecha_str,
            "Hora": ahora.strftime("%H:%M"),
            "Semana": semana_num,
            "Lote": lote_norm,
            "Parcelero": "Corte Tableta CSV",
            "Color_Cinta": color_norm,
            "Racimos": -cant,
            "Estado": "Cortado"
        })
    return descuentos
st.title("Gestión Finca Lola (86.1 Ha)")

if len(st.session_state.cola_offline) > 0:
    st.warning(f"Tienes {len(st.session_state.cola_offline)} registro(s) guardados en el celular.")
    if st.button("Sincronizar ahora con Google Sheets", type="primary"):
        try:
            agregar_filas(st.session_state.cola_offline)
            st.session_state.cola_offline = []
            st.success("Registros sincronizados correctamente.")
            st.rerun()
        except Exception as e:
            st.error(f"Error al sincronizar: {repr(e)}")

rol = st.radio("Selecciona perfil:", ["Parcelero (Embolse)", "Puyero (Consulta)", "Administrador"], horizontal=True)

if rol == "Parcelero (Embolse)":
    st.subheader("Registro de Fruta Embolsada")
    lote_detectado = "Lote 01"
    if st.toggle("Activar cámara para escanear QR", key="qr_parcelero"):
        foto_qr = st.camera_input("Apunta al QR del Lote")
        if foto_qr:
            img_bgr = cv2.cvtColor(np.array(Image.open(foto_qr)), cv2.COLOR_RGB2BGR)
            dato_qr, _, _ = cv2.QRCodeDetector().detectAndDecode(img_bgr)
            if dato_qr in LOTES:
                lote_detectado = dato_qr
                st.success(f"Lote detectado: {lote_detectado}")
    lote_sel = st.selectbox("Lote:", LOTES, index=LOTES.index(lote_detectado))
    sel_p = st.selectbox("Parcelero:", PARCELEROS_BASE)
    if sel_p == "Otro (Escribir nombre)":
        parcelero = st.text_input("Nombre del trabajador del día:").strip() or "Trabajador Extra"
    else:
        parcelero = sel_p
    st.write("Toca el color de la cinta:")
    VISUAL_CINTAS = {
        "🟡 Amarilla": "Amarilla", "🟣 Morada": "Morada",
        "🔴 Roja": "Roja", "🟤 Café": "Café",
        "⚫ Negra": "Negra", "🟢 Verde": "Verde",
        "🔵 Azul": "Azul", "⚪ Blanca": "Blanca"
    }
    if "cinta_elegida" not in st.session_state:
        st.session_state.cinta_elegida = "Amarilla"
    cols_cinta = st.columns(4)
    for idx, (etiqueta, nombre_real) in enumerate(VISUAL_CINTAS.items()):
        with cols_cinta[idx % 4]:
            if st.button(etiqueta, key=f"cinta_{nombre_real}", use_container_width=True):
                st.session_state.cinta_elegida = nombre_real
    cinta = st.session_state.cinta_elegida
    st.info(f"Cinta seleccionada: **{cinta}**")
    racimos = st.number_input("Cantidad de racimos embolsados:", min_value=1, max_value=1000, value=35)
    if st.button("Guardar Embolse", type="primary"):
        ahora = datetime.now()
        registro = {
            "Fecha": ahora.strftime("%Y-%m-%d"),
            "Hora": ahora.strftime("%H:%M"),
            "Semana": ahora.isocalendar().week,
            "Lote": lote_sel,
            "Parcelero": parcelero,
            "Color_Cinta": cinta,
            "Racimos": int(racimos),
            "Estado": "En campo"
        }
        try:
            agregar_filas([registro])
            st.success(f"Guardados {racimos} racimos ({cinta}) en {lote_sel}.")
        except Exception as e:
            st.error(f"Error técnico: {repr(e)}")

elif rol == "Puyero (Consulta)":
    st.subheader("Consulta de Fruta Colgada en el Lote")
    st.caption("Activa la cámara para escanear el QR del lote o selecciónalo en la lista.")
    lote_q = "Lote 01"
    if st.toggle("Activar cámara para escanear QR", key="qr_puyero"):
        foto_qr_p = st.camera_input("Apunta al QR del Lote")
        if foto_qr_p:
            img_bgr = cv2.cvtColor(np.array(Image.open(foto_qr_p)), cv2.COLOR_RGB2BGR)
            dato_qr, _, _ = cv2.QRCodeDetector().detectAndDecode(img_bgr)
            if dato_qr in LOTES:
                lote_q = dato_qr
                st.success(f"Ubicación: {lote_q}")
    lote_rev = st.selectbox("Lote a consultar:", LOTES, index=LOTES.index(lote_q))
    df = cargar_datos()
    if not df.empty:
        df_lote = df[df["Lote"] == lote_rev]
        saldo = df_lote.groupby("Color_Cinta")["Racimos"].sum().reset_index()
        saldo = saldo[saldo["Racimos"] > 0]
        if saldo.empty:
            st.info(f"No hay fruta registrada pendiente en {lote_rev}.")
        else:
            st.write(f"Saldo actual en {lote_rev}:")
            st.dataframe(saldo.rename(columns={"Racimos": "Racimos_Disponibles"}), use_container_width=True)
            st.metric("Total en este lote", f"{int(saldo['Racimos'].sum())} racimos")
elif rol == "Administrador":
    clave = st.text_input("Clave de Administrador:", type="password")
    if clave != CLAVE_ADMIN:
        if clave != "":
            st.error("Clave incorrecta.")
        st.stop()
    tab1, tab2, tab3 = st.tabs(["Inventario y Cajas", "Historial y Filtros de Corte", "Subir CSV de Tableta"])
    df = cargar_datos()
with tab1:
        st.subheader("Proyección y Balance por Edad (86.1 Ha)")
        col_r1, col_r2 = st.columns(2)
        ratio = col_r1.number_input("Ratio (Cajas / Racimo):", value=1.15, min_value=0.50, max_value=2.50, step=0.05)
        merma = col_r2.slider("Merma estimada (%):", 0, 20, 5)
        if df.empty:
            st.warning("Aún no hay movimientos registrados.")
        else:
            semana_actual = datetime.now().isocalendar().week
            
            # 1. Separar entradas (Embolses por Semana) y salidas totales (Cortes)
            entradas = df[df["Racimos"] > 0].groupby(["Lote", "Color_Cinta", "Semana"])["Racimos"].sum().reset_index()
            entradas = entradas.sort_values(by=["Lote", "Color_Cinta", "Semana"], ascending=[True, True, True])
            
            salidas = df[df["Racimos"] < 0].groupby(["Lote", "Color_Cinta"])["Racimos"].sum().abs().to_dict()
            
            # 2. Aplicar descuento FIFO (Primero a la semana mas vieja)
            filas_balance = []
            for _, fila in entradas.iterrows():
                lote = fila["Lote"]
                color = fila["Color_Cinta"]
                sem = int(fila["Semana"])
                emb = int(fila["Racimos"])
                
                cortes_pendientes = salidas.get((lote, color), 0)
                descontar = min(emb, cortes_pendientes)
                salidas[(lote, color)] = cortes_pendientes - descontar
                saldo = emb - descontar
                
                # Calcular edad en semanas (ajustando cambio de anio si aplica)
                edad = semana_actual - sem if semana_actual >= sem else (52 - sem) + semana_actual
                
                filas_balance.append({
                    "Lote": lote,
                    "Color_Cinta": color,
                    "Semana_Emb": sem,
                    "Edad_Semanas": f"{edad} sem",
                    "Embolsados": emb,
                    "Cortados": descontar,
                    "Saldo_En_Mata": saldo
                })
                
            balance = pd.DataFrame(filas_balance)
            
            if not balance.empty:
                solo_positivos = balance[balance["Saldo_En_Mata"] > 0]
                total_racimos = int(solo_positivos["Saldo_En_Mata"].sum())
                cajas_est = total_racimos * (1 - merma / 100.0) * ratio
                
                m1, m2 = st.columns(2)
                m1.metric("Saldo Real en Mata", f"{total_racimos:,} racimos")
                m2.metric("Cajas Proyectadas (20 kg)", f"{cajas_est:,.0f} cajas")
                
                st.write("Balance por Color y Edad (Toda la Finca)")
                bal_edad = balance.groupby(["Color_Cinta", "Semana_Emb", "Edad_Semanas"]).agg(
                    Embolsados=("Embolsados", "sum"),
                    Cortados=("Cortados", "sum"),
                    Saldo_En_Mata=("Saldo_En_Mata", "sum")
                ).reset_index()
                bal_edad["Cajas_Est"] = (bal_edad["Saldo_En_Mata"] * (1 - merma / 100.0) * ratio).round(0).astype(int)
                st.dataframe(bal_edad, use_container_width=True)
                
                st.write("Balance Detallado por Lote y Edad (FIFO)")
                balance["Cajas_Est"] = (balance["Saldo_En_Mata"] * (1 - merma / 100.0) * ratio).round(0).astype(int)
                st.dataframe(balance, use_container_width=True)
    with tab2:
        st.subheader("Buscador y Totales de Corte")
        solo_cortes = df[df["Racimos"] < 0].copy() if not df.empty else pd.DataFrame()
        if solo_cortes.empty:
            st.info("Aún no hay cortes registrados desde la tableta.")
        else:
            solo_cortes["Racimos_Cortados"] = solo_cortes["Racimos"].abs()
            solo_cortes["Fecha"] = solo_cortes["Fecha"].astype(str)
            f1, f2, f3 = st.columns(3)
            fechas_disp = ["Todas"] + sorted(solo_cortes["Fecha"].unique().tolist(), reverse=True)
            lotes_disp = ["Todos"] + sorted(solo_cortes["Lote"].unique().tolist())
            colores_disp = ["Todos"] + sorted(solo_cortes["Color_Cinta"].unique().tolist())
            filtro_fecha = f1.selectbox("Filtrar por Fecha:", fechas_disp)
            filtro_lote = f2.selectbox("Filtrar por Lote:", lotes_disp)
            filtro_color = f3.selectbox("Filtrar por Color:", colores_disp)
            df_filtrado = solo_cortes.copy()
            if filtro_fecha != "Todas":
                df_filtrado = df_filtrado[df_filtrado["Fecha"] == filtro_fecha]
            if filtro_lote != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Lote"] == filtro_lote]
            if filtro_color != "Todos":
                df_filtrado = df_filtrado[df_filtrado["Color_Cinta"] == filtro_color]
            total_cortados = int(df_filtrado["Racimos_Cortados"].sum())
            cajas_cortadas = total_cortados * ratio
            t1, t2 = st.columns(2)
            t1.metric("Total Racimos Cortados (Filtro)", f"{total_cortados:,} racimos")
            t2.metric("Cajas Equivalentes (Según Ratio)", f"{cajas_cortadas:,.0f} cajas")
            tabla_mostrar = df_filtrado[["Fecha", "Semana", "Lote", "Color_Cinta", "Racimos_Cortados"]].sort_values(by="Fecha", ascending=False)
            st.dataframe(tabla_mostrar, use_container_width=True)
            csv_descarga = tabla_mostrar.to_csv(index=False).encode("utf-8")
            st.download_button("Descargar Selección en Excel (CSV)", data=csv_descarga, file_name="reporte_cortes_filtrado.csv", mime="text/csv")
    with tab3:
        st.subheader("Descontar Corte con CSV Directo de Tableta")
        st.write("Sube el archivo .csv de la tableta (cada fila cuenta como 1 racimo).")
        archivo_csv = st.file_uploader("Seleccionar archivo .csv de la tableta", type=["csv"])
        if archivo_csv is not None:
            try:
                df_tab = pd.read_csv(archivo_csv, sep=None, engine="python")
            except Exception:
                archivo_csv.seek(0)
                df_tab = pd.read_csv(archivo_csv)
            st.write("Vista previa del CSV cargado:")
            st.dataframe(df_tab.head(10), use_container_width=True)
            columnas_archivo = df_tab.columns.tolist()
            c1, c2, c3 = st.columns(3)
            col_lote = c1.selectbox("Columna de Lote:", columnas_archivo)
            col_color = c2.selectbox("Columna de Color:", columnas_archivo)
            col_fecha = c3.selectbox("Columna de Fecha:", ["Usar fecha de hoy"] + columnas_archivo)
            if st.button("Procesar CSV y Descontar Inventario", type="primary"):
                descuentos = procesar_csv_tableta(df_tab, col_lote, col_color, col_fecha)
                if descuentos:
                    try:
                        agregar_filas(descuentos)
                        total_desc = sum(abs(d["Racimos"]) for d in descuentos)
                        st.success(f"Listo. Se descontaron {total_desc} racimos respetando las fechas del CSV.")
                    except Exception as e:
                        st.error(f"Error técnico al descontar: {repr(e)}")
                else:
                    st.error("No se encontraron registros válidos en el CSV.")

