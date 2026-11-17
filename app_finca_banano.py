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
PARCELEROS_BASE = [f"Parcelero {i:02d}" for i in range(1, 11)] + ["Otro (Escribir nombre)"]
CLAVE_ADMIN = "banano2026"
ID_HOJA = "1WnHs71IMeuz9X9sAtJkNYJbR9QJE2QqAKq37-PGsr-0"
NOMBRE_HOJA = "Hoja 1"

if "cola_offline" not in st.session_state:
    st.session_state.cola_offline = []

def conectar_hoja():
    sec = st.secrets["connections"]["gsheets"]
    llave_privada = sec["private_key"].replace("\\n", "\n")
    url_token = "https://" + "://googleapis.com" + "/token"
    url_auth = "https://" + "://google.com" + "/o/oauth2/auth"
    url_certs = "https://" + "://googleapis.com" + "/oauth2/v1/certs"
    info_credenciales = {
        "type": "service_account",
        "project_id": sec["project_id"],
        "private_key_id": sec["private_key_id"],
        "private_key": llave_privada,
        "client_email": sec["client_email"],
        "client_id": sec["client_id"],
        "auth_uri": url_auth,
        "token_uri": url_token,
        "auth_provider_x509_cert_url": url_certs,
        "client_x509_cert_url": sec.get("client_x509_cert_url", "")
    }
    alcances = [
        "https://" + "://googleapis.com" + "/auth/spreadsheets",
        "https://" + "://googleapis.com" + "/auth/drive"
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

def procesar_csv_tableta(df_tab, col_lote, col_color, col_cant):
    ahora = datetime.now()
    descuentos = []
    for _, fila in df_tab.iterrows():
        cant = pd.to_numeric(fila[col_cant], errors="coerce")
        if pd.notna(cant) and cant > 0:
            lote_raw = str(fila[col_lote]).strip()
            num_lote = "".join(filter(str.isdigit, lote_raw))
            lote_norm = f"Lote {int(num_lote):02d}" if num_lote else lote_raw
            color_norm = str(fila[col_color]).strip().capitalize()
            descuentos.append({
                "Fecha": ahora.strftime("%Y-%m-%d"),
                "Hora": ahora.strftime("%H:%M"),
                "Semana": ahora.isocalendar().week,
                "Lote": lote_norm,
                "Parcelero": "Corte Tableta CSV",
                "Color_Cinta": color_norm,
                "Racimos": -int(cant),
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
    cinta = st.selectbox("Color de Cinta:", COLORES_CINTA)
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
    tab1, tab2 = st.tabs(["Inventario y Cajas", "Subir CSV de Tableta"])
    with tab1:
        st.subheader("Proyección de Cosecha (86.1 Ha)")
        col_r1, col_r2 = st.columns(2)
        ratio = col_r1.number_input("Ratio (Cajas / Racimo):", value=1.15, min_value=0.50, max_value=2.50, step=0.05)
        merma = col_r2.slider("Merma estimada (%):", 0, 20, 5)
        df = cargar_datos()
        if df.empty:
            st.warning("Aún no hay movimientos registrados.")
        else:
            saldo_general = df.groupby(["Lote", "Color_Cinta"])["Racimos"].sum().reset_index()
            saldo_activo = saldo_general[saldo_general["Racimos"] > 0].copy()
            total_racimos = int(saldo_activo["Racimos"].sum())
            cajas_est = total_racimos * (1 - merma / 100.0) * ratio
            m1, m2 = st.columns(2)
            m1.metric("Saldo Real en Mata", f"{total_racimos:,} racimos")
            m2.metric("Cajas Proyectadas (20 kg)", f"{cajas_est:,.0f} cajas")
            st.write("Saldo por Color de Cinta (Toda la Finca)")
            por_cinta = saldo_activo.groupby("Color_Cinta")["Racimos"].sum().reset_index()
            por_cinta["Cajas_Est"] = (por_cinta["Racimos"] * (1 - merma / 100.0) * ratio).round(0).astype(int)
            st.dataframe(por_cinta, use_container_width=True)
            st.write("Saldo Detallado por Lote (Fruta que quedó en mata)")
            saldo_activo["Cajas_Est"] = (saldo_activo["Racimos"] * (1 - merma / 100.0) * ratio).round(0).astype(int)
            st.dataframe(saldo_activo, use_container_width=True)
            st.write("Embolse por Trabajador")
            solo_embolse = df[df["Racimos"] > 0]
            por_trabajador = solo_embolse.groupby(["Parcelero", "Fecha"])["Racimos"].sum().reset_index()
            st.dataframe(por_trabajador, use_container_width=True)
    with tab2:
        st.subheader("Descontar Corte con CSV Directo de Tableta")
        st.write("Sube el archivo .csv que genera la tableta.")
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
            col_cant = c3.selectbox("Columna de Cantidad:", columnas_archivo)
            if st.button("Procesar CSV y Descontar Inventario", type="primary"):
                descuentos = procesar_csv_tableta(df_tab, col_lote, col_color, col_cant)
                if descuentos:
                    try:
                        agregar_filas(descuentos)
                        st.success(f"Listo. Se descontaron {len(descuentos)} registros del CSV.")
                    except Exception as e:
                        st.error(f"Error técnico al descontar: {repr(e)}")
                else:
                    st.error("No se encontraron cantidades válidas.")
