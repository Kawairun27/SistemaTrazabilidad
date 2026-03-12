import streamlit as st
import os
import hashlib
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from fpdf import FPDF
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TechArmor RD - Sistema Integrado", layout="wide")

# --- DB SETUP ---
engine = create_engine('sqlite:///trazabilidad_v2.db')
Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True)
    password = Column(String)
    nombre = Column(String)

class Pedido(Base):
    __tablename__ = 'pedidos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, default=datetime.now)
    usuario_id = Column(Integer)

class Unidad(Base):
    __tablename__ = 'unidades'
    codigo_xz = Column(String, primary_key=True)
    modelo = Column(String)
    etapa = Column(String)
    pedido_id = Column(Integer)
    ultima_actualizacion = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# --- FUNCIONES DE APOYO ---
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def render_avatar(nombre):
    """Genera un avatar circular con la inicial y el nombre al lado."""
    inicial = nombre[0].upper() if nombre else "?"
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <div style="background-color: #2e7d32; color: white; border-radius: 50%; 
                        width: 50px; height: 50px; display: flex; justify-content: center; 
                        align-items: center; font-size: 20px; font-weight: bold; margin-right: 15px;">
                {inicial}
            </div>
            <div style="font-size: 18px; font-weight: 500;">{nombre}</div>
        </div>
    """, unsafe_allow_html=True)

def crear_pdf_cotizacion(codigo, producto, num_orden):
    pdf = FPDF()
    pdf.add_page()
    INFO = {
        "Apex-15 Stealth": {"specs": "i7-13700H, RTX 4070, 16GB RAM", "tiempo": "5 días", "img": "images/Apex-15Stealth.webp"},
        "Titan-18 Ultra": {"specs": "i9-14900HX, RTX 4090, 32GB RAM", "tiempo": "7 días", "img": "images/Titan18Ultra.webp"},
        "Horizon-G Pro": {"specs": "Ryzen 9, RTX 4080, Liquid Cooling", "tiempo": "6 días", "img": "images/HorizonG-pro.webp"},
        "Workstation-X": {"specs": "Xeon Gold, 64GB ECC, Quadro RTX", "tiempo": "8 días", "img": "images/WorkstationX.png"},
        "GPU-Vortex 90": {"specs": "24GB GDDR6X, Triple Fan, DLSS 3.5", "tiempo": "3 días", "img": "images/GpuVortex.webp"},
        "RAM-Fury 64GB": {"specs": "DDR5 6000MHz, CL30, RGB", "tiempo": "2 días", "img": "images/RAM-Fury-64gb.webp"}
    }
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(40, 70, 120)
    pdf.cell(200, 15, txt="TECHARMOR RD - HOJA DE TRAZABILIDAD", ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(200, 10, txt=f"ORDEN DE PRODUCCIÓN: #{num_orden:03d} | ID: {codigo}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(100, 10, txt=f"Modelo: {producto}", ln=True)
    if producto in INFO:
        pdf.multi_cell(0, 10, txt=f"Especificaciones Técnicas: {INFO[producto]['specs']}")
        pdf.cell(100, 10, txt=f"Tiempo Estándar de Entrega: {INFO[producto]['tiempo']}", ln=True)
        pdf.ln(5)
        ruta_img = INFO[producto]['img']
        if os.path.exists(ruta_img):
            if ruta_img.lower().endswith(".webp"):
                img_temp = Image.open(ruta_img).convert("RGB")
                img_temp_path = ruta_img.replace(".webp", "_temp.jpg")
                img_temp.save(img_temp_path, "JPEG")
                pdf.image(img_temp_path, x=55, y=pdf.get_y(), w=100)
                os.remove(img_temp_path)
            else:
                pdf.image(ruta_img, x=55, y=pdf.get_y(), w=100)
    pdf.set_y(-40)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, txt="Documento generado bajo estándares de Normalización ISO 9001:2015 - Grupo I", align='C', ln=True)
    nombre_archivo = f"HojaTecnica_{codigo}.pdf"
    pdf.output(nombre_archivo)
    return nombre_archivo

# --- LÓGICA DE NAVEGACIÓN ---
query_params = st.query_params
es_admin = query_params.get("acceso") == "root"

if es_admin:
    menu = st.sidebar.selectbox("🛡️ MODO ADMINISTRADOR", ["🏭 Producción ISO", "🛒 Vista Tienda"])
else:
    menu = "🛒 Vista Tienda"

# --- BLOQUE TIENDA ---
if menu == "🛒 Vista Tienda":
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    if 'user_name' not in st.session_state: st.session_state.user_name = ""

    with st.sidebar:
        st.title("👤 Mi Cuenta")
        if not st.session_state.logged_in:
            opcion_auth = st.radio("Selecciona una opción", ["Iniciar Sesión", "Registrarse"])
            
            if opcion_auth == "Iniciar Sesión":
                with st.form("login_form"):
                    l_em = st.text_input("Email")
                    l_pw = st.text_input("Clave", type="password")
                    if st.form_submit_button("Entrar"):
                        u = session.query(Usuario).filter(Usuario.email == l_em, Usuario.password == hash_password(l_pw)).first()
                        if u:
                            st.session_state.logged_in = True
                            st.session_state.user_email = u.email
                            st.session_state.user_name = u.nombre
                            st.session_state.user_id = u.id
                            st.rerun()
                        else:
                            st.error("Credenciales incorrectas")
            else:
                with st.form("reg"):
                    n_nom, n_em, n_pw = st.text_input("Nombre"), st.text_input("Email"), st.text_input("Clave", type="password")
                    if st.form_submit_button("Crear Cuenta"):
                        try:
                            nuevo_u = Usuario(nombre=n_nom, email=n_em, password=hash_password(n_pw))
                            session.add(nuevo_u)
                            session.commit()
                            st.success("¡Cuenta creada! Ya puedes iniciar sesión.")
                        except: st.error("El email ya existe.")
        else:
            render_avatar(st.session_state.user_name)
            if st.button("Cerrar Sesión"):
                st.session_state.logged_in = False
                st.rerun()

    st.title("🛡️ TechArmor Premium Systems")
    tab1, tab2 = st.tabs(["🛒 Catálogo", "🔍 Rastrear Pedido"])

    with tab1:
        PRODUCTOS_INFO = {
            "Apex-15 Stealth": {"img": "images/Apex-15Stealth.webp", "precio": 85900},
            "Titan-18 Ultra": {"img": "images/Titan18Ultra.webp", "precio": 145000},
            "Horizon-G Pro": {"img": "images/HorizonG-pro.webp", "precio": 95000},
            "Workstation-X": {"img": "images/WorkstationX.png", "precio": 110000},
            "GPU-Vortex 90": {"img": "images/GpuVortex.webp", "precio": 62500},
            "RAM-Fury 64GB": {"img": "images/RAM-Fury-64gb.webp", "precio": 18200}
        }
        col_p, col_c = st.columns([3, 1])
        with col_p:
            p_items = list(PRODUCTOS_INFO.items())
            for i in range(0, len(p_items), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i+j < len(p_items):
                        name, info = p_items[i+j]
                        with cols[j]:
                            if os.path.exists(info["img"]): st.image(info["img"], use_container_width=True)
                            st.subheader(name)
                            if st.button(f"Añadir RD${info['precio']:,}", key=f"b_{name}"):
                                st.session_state.carrito.append(name); st.toast(f"✅ {name}")
        with col_c:
            st.subheader("Carrito")
            for item in st.session_state.carrito: st.write(f"- {item}")
            if st.session_state.carrito and st.button("🚀 Pagar ahora"):
                if not st.session_state.logged_in: 
                    st.warning("⚠️ Debes iniciar sesión para comprar.")
                else:
                    ped = Pedido(usuario_id=st.session_state.user_id)
                    session.add(ped); session.commit()
                    for p in st.session_state.carrito:
                        id_u = f"XZ-{p[:2].upper()}-{datetime.now().strftime('%M%S')}"
                        session.add(Unidad(codigo_xz=id_u, modelo=p, etapa="Recibido", pedido_id=ped.id))
                    session.commit(); st.session_state.carrito = []; st.success(f"¡Orden #{ped.id} creada!"); st.balloons()

    with tab2:
        st.subheader("Rastreo de Unidades")
        num = st.number_input("Introduce tu número de Orden:", min_value=1, step=1)
        if st.button("Buscar Estado"):
            res = session.query(Unidad).filter(Unidad.pedido_id == num).all()
            if res:
                for it in res:
                    with st.container(border=True):
                        st.write(f"📦 **Modelo:** {it.modelo} | **ID:** {it.codigo_xz}")
                        progreso = {"Recibido": 15, "En Proceso": 50, "Terminación": 85, "Despacho": 100}.get(it.etapa, 0)
                        st.progress(progreso)
                        st.caption(f"Estado actual: {it.etapa}")
            else:
                st.error("No se encontró ninguna orden con ese número.")

# --- BLOQUE PRODUCCIÓN ---
elif menu == "🏭 Producción ISO":
    st.title("🏭 Panel de Producción ISO")
    pendientes = session.query(Unidad).filter(Unidad.etapa != "Despacho").all()
    col1, col2 = st.columns(2)
    col1.metric("Órdenes Activas", len(pendientes))
    
    for u in pendientes:
        with st.expander(f"📦 Orden #{u.pedido_id} | {u.codigo_xz}"):
            nueva = st.select_slider("Etapa:", ["Recibido", "En Proceso", "Terminación", "Despacho"], value=u.etapa, key=f"u_{u.codigo_xz}")
            if st.button(f"📄 Generar Hoja Técnica", key=f"pdf_{u.codigo_xz}"):
                f = crear_pdf_cotizacion(u.codigo_xz, u.modelo, u.pedido_id)
                with open(f, "rb") as file: st.download_button("Descargar PDF", file, file_name=f)
            if nueva != u.etapa:
                u.etapa = nueva; session.commit(); st.rerun()

st.divider()
st.caption("TechArmor RD - Grupo I | Normalización y Metrología")