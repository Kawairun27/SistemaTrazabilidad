import streamlit as st
import os
import hashlib
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from fpdf import FPDF
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TechArmor RD - Sistema Integrado", layout="wide")

# --- DB SETUP ---
engine = create_engine('sqlite:///trazabilidad_v3.db')
Base = declarative_base()

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True)
    password = Column(String)
    nombre = Column(String)
    pedidos = relationship("Pedido", back_populates="usuario")

class Pedido(Base):
    __tablename__ = 'pedidos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(DateTime, default=datetime.now)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'))
    usuario = relationship("Usuario", back_populates="pedidos")
    unidades = relationship("Unidad", back_populates="pedido")

class Unidad(Base):
    __tablename__ = 'unidades'
    codigo_xz = Column(String, primary_key=True)
    modelo = Column(String)
    etapa = Column(String)
    pedido_id = Column(Integer, ForeignKey('pedidos.id'))
    pedido = relationship("Pedido", back_populates="unidades")
    ultima_actualizacion = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# --- DATOS DE PRODUCTOS ---
PRODUCTOS_INFO = {
    "Apex-15 Stealth": {"img": "images/Apex-15Stealth.webp", "precio": 85900},
    "Titan-18 Ultra": {"img": "images/Titan18Ultra.webp", "precio": 145000},
    "Horizon-G Pro": {"img": "images/HorizonG-pro.webp", "precio": 95000},
    "Workstation-X": {"img": "images/WorkstationX.png", "precio": 110000},
    "GPU-Vortex 90": {"img": "images/GpuVortex.webp", "precio": 62500},
    "RAM-Fury 64GB": {"img": "images/RAM-Fury-64gb.webp", "precio": 18200}
}

# --- FUNCIONES DE APOYO ---
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def generar_pdf_trazabilidad(unidad):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "CERTIFICADO DE TRAZABILIDAD - TECHARMOR RD", ln=True, align='C')
    pdf.ln(10)
    
    # Imagen del producto si existe
    img_path = PRODUCTOS_INFO.get(unidad.modelo, {}).get("img")
    if img_path and os.path.exists(img_path):
        try:
            pdf.image(img_path, x=75, y=30, w=60)
            pdf.ln(65)
        except: pass

    pdf.set_font("Arial", size=12)
    data = [
        ["ID de Unidad", unidad.codigo_xz],
        ["Modelo", unidad.modelo],
        ["Estado Actual", unidad.etapa],
        ["Orden Asociada", f"#{unidad.pedido_id}"],
        ["Fecha Emisión", datetime.now().strftime("%d/%m/%Y %H:%M")]
    ]
    
    for row in data:
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(50, 10, row[0] + ":")
        pdf.set_font("Arial", size=12)
        pdf.cell(100, 10, row[1], ln=True)
    
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 10)
    pdf.multi_cell(0, 10, "Este documento certifica que el hardware mencionado ha pasado por los procesos de calidad ISO de TechArmor RD.")
    
    return pdf.output(dest='S').encode('latin-1')

def enviar_correo_premium(destinatario, nombre_cliente, id_orden, items):
    sender_email = "tu_correo@gmail.com"
    # Lógica de envío simulada mediante st.toast
    try:
        st.toast(f"📧 Correo de confirmación enviado a {destinatario}")
    except: pass

def render_avatar(nombre):
    inicial = nombre[0].upper() if nombre else "?"
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <div style="background-color: #1e3a8a; color: white; border-radius: 50%; 
                        width: 50px; height: 50px; display: flex; justify-content: center; 
                        align-items: center; font-size: 20px; font-weight: bold; margin-right: 15px;
                        border: 2px solid #3b82f6;">
                {inicial}
            </div>
            <div>
                <div style="font-size: 13px; color: #666;">Sesión iniciada como</div>
                <div style="font-size: 16px; font-weight: bold; color: #1e3a8a;">{nombre}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- NAVEGACIÓN ---
query_params = st.query_params
es_admin = query_params.get("acceso") == "root"
menu = st.sidebar.selectbox("🛡️ Menú", ["🛒 Vista Tienda", "🏭 Producción ISO"]) if es_admin else "🛒 Vista Tienda"

# --- BLOQUE TIENDA ---
if menu == "🛒 Vista Tienda":
    st.title("🛡️ TechArmor Premium Systems")
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'carrito' not in st.session_state: st.session_state.carrito = []

    with st.sidebar:
        st.title("👤 Mi Cuenta")
        if not st.session_state.logged_in:
            auth = st.tabs(["Entrar", "Crear"])
            with auth[0]:
                with st.form("login_form"):
                    em = st.text_input("Email")
                    pw = st.text_input("Clave", type="password")
                    if st.form_submit_button("Iniciar Sesión"):
                        user = session.query(Usuario).filter(Usuario.email == em, Usuario.password == hash_password(pw)).first()
                        if user:
                            st.session_state.update({"logged_in": True, "user_email": user.email, "user_name": user.nombre, "user_id": user.id})
                            st.rerun()
                        else: st.error("Email o clave incorrectos")
            with auth[1]:
                with st.form("register_form"):
                    n, e, p = st.text_input("Nombre"), st.text_input("Email"), st.text_input("Clave", type="password")
                    if st.form_submit_button("Registrar"):
                        try:
                            session.add(Usuario(nombre=n, email=e, password=hash_password(p)))
                            session.commit()
                            st.success("¡Registrado!")
                        except: st.error("Error en registro.")
        else:
            render_avatar(st.session_state.user_name)
            if st.button("Cerrar Sesión"):
                st.session_state.logged_in = False
                st.rerun()

    t1, t2 = st.tabs(["🛒 Catálogo Tech", "🔍 Rastrear Pedido"])
    
    with t1:
        col_prod, col_cart = st.columns([3, 1])
        with col_prod:
            p_items = list(PRODUCTOS_INFO.items())
            for i in range(0, len(p_items), 2):
                row = st.columns(2)
                for j in range(2):
                    if i + j < len(p_items):
                        name, info = p_items[i + j]
                        with row[j]:
                            if os.path.exists(info["img"]): st.image(info["img"], use_container_width=True)
                            st.subheader(name)
                            st.write(f"**Precio: RD${info['precio']:,}**")
                            if st.button(f"🛒 Añadir", key=f"btn_{name}"):
                                st.session_state.carrito.append(name)
                                st.toast(f"✅ {name} añadido")
        with col_cart:
            st.subheader("Tu Carrito")
            for item in st.session_state.carrito: st.write(f"- {item}")
            if st.session_state.carrito and st.button("🚀 Pagar ahora"):
                if not st.session_state.logged_in: st.warning("Inicia sesión")
                else:
                    ped = Pedido(usuario_id=st.session_state.user_id)
                    session.add(ped); session.commit()
                    for it in st.session_state.carrito:
                        cod = f"XZ-{it[:2].upper()}-{datetime.now().strftime('%M%S')}"
                        session.add(Unidad(codigo_xz=cod, modelo=it, etapa="Recibido", pedido_id=ped.id))
                    session.commit()
                    enviar_correo_premium(st.session_state.user_email, st.session_state.user_name, ped.id, st.session_state.carrito)
                    st.session_state.carrito = []; st.success(f"Orden #{ped.id} creada"); st.balloons()

    with t2:
        st.subheader("🔍 Rastreo Automático")
        num_ord = st.number_input("Número de Orden:", min_value=0, step=1)
        if num_ord > 0:
            unidades = session.query(Unidad).filter(Unidad.pedido_id == num_ord).all()
            if unidades:
                for u in unidades:
                    with st.container(border=True):
                        st.write(f"📦 **{u.modelo}** | ID: `{u.codigo_xz}`")
                        st.progress({"Recibido": 15, "En Proceso": 50, "Terminación": 85, "Despacho": 100}.get(u.etapa, 0))
                        st.caption(f"Etapa: {u.etapa}")
            else: st.error("No encontrado.")

# --- BLOQUE PRODUCCIÓN ---
elif menu == "🏭 Producción ISO":
    st.title("🏭 Centro de Trazabilidad Industrial")
    todas = session.query(Unidad).join(Pedido).join(Usuario).all()
    pend = [u for u in todas if u.etapa != "Despacho"]
    comp = [u for u in todas if u.etapa == "Despacho"]

    tp, tc = st.tabs([f"🕒 Pendientes ({len(pend)})", f"✅ Completadas ({len(comp)})"])
    
    with tp:
        if not pend:
            st.info("No hay órdenes pendientes en línea de producción.")
        for u in pend:
            icon = "🔴" if u.etapa == "Recibido" else "🟡"
            with st.expander(f"{icon} Orden #{u.pedido_id} | Cliente: {u.pedido.usuario.nombre}"):
                st.write(f"**Email:** {u.pedido.usuario.email} | **Modelo:** {u.modelo}")
                
                # --- NUEVA UBICACIÓN DEL BOTÓN PDF ---
                pdf_data = generar_pdf_trazabilidad(u)
                st.download_button(
                    label=f"📄 Generar Certificado Parcial {u.codigo_xz}", 
                    data=pdf_data, 
                    file_name=f"TechArmor_PEND_{u.codigo_xz}.pdf", 
                    mime="application/pdf",
                    key=f"dl_pend_{u.codigo_xz}" # Key única para pendientes
                )
                
                st.divider()
                
                nueva = st.select_slider(
                    "Actualizar Etapa de Producción:", 
                    ["Recibido", "En Proceso", "Terminación", "Despacho"], 
                    value=u.etapa, 
                    key=f"prod_{u.codigo_xz}"
                )
                
                if nueva != u.etapa:
                    u.etapa = nueva
                    session.commit()
                    st.rerun()
                    
    with tc:
        if not comp:
            st.info("Aún no hay órdenes finalizadas.")
        for u in comp:
            with st.container(border=True):
                st.success(f"✔️ Orden #{u.pedido_id} - {u.modelo} (Cliente: {u.pedido.usuario.nombre})")
                
                # Mantenemos el botón aquí también por si se necesita una copia final
                pdf_data = generar_pdf_trazabilidad(u)
                st.download_button(
                    label=f"📄 Descargar Certificado Final {u.codigo_xz}", 
                    data=pdf_data, 
                    file_name=f"TechArmor_FINAL_{u.codigo_xz}.pdf", 
                    mime="application/pdf",
                    key=f"dl_comp_{u.codigo_xz}"
                )

st.divider()
st.caption("TechArmor RD - Grupo I | Calidad Certificada")