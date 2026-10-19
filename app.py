import os
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
import streamlit as st
from sqlalchemy import (
    create_engine, text, MetaData, Table, Column, Integer, String, Text,
    DateTime, Date, Numeric, ForeignKey, Boolean, select, func
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

# ---------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="BeniFerch | Gestión",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

GOLD = "#D4AF37"
DARK = "#111111"
DATABASE_URL = None
try:
    DATABASE_URL = st.secrets.get("DATABASE_URL")
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL")

# SQLite es útil para pruebas locales. En Streamlit Community Cloud se
# recomienda PostgreSQL/Supabase para que los datos sobrevivan despliegues.
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
    elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
    CLOUD_DB = True
else:
    engine = create_engine("sqlite:///beniferch.db", future=True, connect_args={"check_same_thread": False})
    CLOUD_DB = False

st.markdown("""
<style>
:root { --bf-gold: #D4AF37; --bf-dark: #111111; }
.stApp { background: #0d0d0f; color: #f5f5f5; }
[data-testid="stHeader"] { background: rgba(13,13,15,.92); }
[data-testid="stSidebar"] { background: #151517; border-right: 1px solid #34302a; }
[data-testid="stSidebar"] { display: none; }
.bf-hero { text-align:center; padding: 8px 0 18px; }
.bf-hero img { width: min(100%, 620px); max-height: 260px; object-fit: contain; border-radius: 16px; }
.bf-tile { background: linear-gradient(145deg,#1b1b1e,#111113); border: 1px solid #514426; border-radius: 16px; padding: 16px 10px; min-height: 110px; text-align:center; }
.bf-tile-icon { font-size: 2rem; }
.bf-tile-title { color:#f7e7a8; font-size:1rem; font-weight:750; margin-top:6px; }
.bf-tile-caption { color:#bdb8ac; font-size:.78rem; margin-top:4px; }

h1,h2,h3 { color: #f7f2e6; }
p, label, .stCaption { color: #d4d4d4; }
div[data-testid="stMetric"] {
  background: linear-gradient(135deg,#1b1b1e,#111113);
  border: 1px solid #3c3420; border-left: 4px solid #D4AF37;
  border-radius: 14px; padding: 16px;
}
div[data-testid="stMetricLabel"] { color: #c9c2b1; }
div[data-testid="stMetricValue"] { color: #f7e7a8; }
.stButton > button, .stFormSubmitButton > button {
  background: #D4AF37; color: #111111; border: 1px solid #D4AF37;
  border-radius: 10px; font-weight: 700; min-height: 42px;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
  background: #f0d36d; color: #111; border-color: #f0d36d;
}
div[data-baseweb="tab-list"] { gap: 8px; }
button[data-baseweb="tab"] { color: #e8dfc7; }
input, textarea { border-radius: 8px !important; }
.bf-brand { font-size: 1.55rem; font-weight: 800; letter-spacing: .06em; color: #D4AF37; }
.bf-sub { color: #a7a7a7; font-size: .86rem; }
.bf-card { padding: 14px 16px; border: 1px solid #383125; border-radius: 14px; background: #171719; }
div[data-testid="stDataFrame"] { border: 1px solid #39342a; border-radius: 10px; }
@media (max-width: 700px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  h1 { font-size: 1.7rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Esquema relacional
# ---------------------------------------------------------------------
md = MetaData()
products = Table(
    "products", md,
    Column("id", Integer, primary_key=True),
    Column("sku", String(60), unique=True, nullable=True),
    Column("name", String(180), nullable=False),
    Column("category", String(80), nullable=False, default="Joyería"),
    Column("material", String(100), nullable=True),
    Column("description", Text, nullable=True),
    Column("cost_price", Numeric(12, 2), nullable=False, default=0),
    Column("sale_price", Numeric(12, 2), nullable=False, default=0),
    Column("stock", Integer, nullable=False, default=0),
    Column("min_stock", Integer, nullable=False, default=0),
    Column("active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime, nullable=False, default=datetime.now),
)
customers = Table(
    "customers", md,
    Column("id", Integer, primary_key=True),
    Column("name", String(180), nullable=False),
    Column("phone", String(40), nullable=True),
    Column("notes", Text, nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.now),
)
sales = Table(
    "sales", md,
    Column("id", Integer, primary_key=True),
    Column("folio", String(40), unique=True, nullable=False),
    Column("customer_id", Integer, ForeignKey("customers.id"), nullable=True),
    Column("customer_name", String(180), nullable=False, default="Público general"),
    Column("sale_date", DateTime, nullable=False, default=datetime.now),
    Column("subtotal", Numeric(12, 2), nullable=False, default=0),
    Column("discount", Numeric(12, 2), nullable=False, default=0),
    Column("total", Numeric(12, 2), nullable=False, default=0),
    Column("paid_total", Numeric(12, 2), nullable=False, default=0),
    Column("balance", Numeric(12, 2), nullable=False, default=0),
    Column("status", String(20), nullable=False, default="PAGADA"),
    Column("notes", Text, nullable=True),
    Column("legacy_id", Integer, nullable=True),
)
sale_items = Table(
    "sale_items", md,
    Column("id", Integer, primary_key=True),
    Column("sale_id", Integer, ForeignKey("sales.id"), nullable=False),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=True),
    Column("product_name", String(180), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Numeric(12, 2), nullable=False),
    Column("unit_cost", Numeric(12, 2), nullable=False, default=0),
    Column("line_total", Numeric(12, 2), nullable=False),
)
payments = Table(
    "payments", md,
    Column("id", Integer, primary_key=True),
    Column("sale_id", Integer, ForeignKey("sales.id"), nullable=False),
    Column("amount", Numeric(12, 2), nullable=False),
    Column("method", String(40), nullable=False, default="Efectivo"),
    Column("paid_at", DateTime, nullable=False, default=datetime.now),
    Column("notes", Text, nullable=True),
    Column("legacy_id", Integer, nullable=True),
)
stock_movements = Table(
    "stock_movements", md,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("movement_type", String(30), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("stock_before", Integer, nullable=False),
    Column("stock_after", Integer, nullable=False),
    Column("reason", String(220), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.now),
)

with engine.begin() as conn:
    md.create_all(conn)

def money(v):
    return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def df_query(sql, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})

def get_products(active_only=True):
    where = "WHERE active = TRUE" if active_only else ""
    return df_query(f"""SELECT id, sku, name, category, material, cost_price, sale_price,
                        stock, min_stock, active FROM products {where} ORDER BY name""")

def get_customers():
    return df_query("SELECT id, name, phone FROM customers ORDER BY name")

def record_stock_movement(conn, product_id, movement_type, quantity, reason):
    row = conn.execute(select(products).where(products.c.id == int(product_id))).mappings().first()
    if not row:
        raise ValueError("El producto ya no existe.")
    before = int(row["stock"])
    after = before + int(quantity)
    if after < 0:
        raise ValueError(f"Stock insuficiente. Disponible: {before}.")
    conn.execute(products.update().where(products.c.id == int(product_id)).values(stock=after))
    conn.execute(stock_movements.insert().values(
        product_id=int(product_id), movement_type=movement_type, quantity=int(quantity),
        stock_before=before, stock_after=after, reason=reason, created_at=datetime.now()
    ))

def create_sale(customer_name, customer_id, cart, discount, payment_amount, payment_method, notes):
    if not cart:
        raise ValueError("Agrega al menos un producto.")
    subtotal = sum((money(item["price"]) * int(item["qty"]) for item in cart.values()), Decimal("0.00"))
    discount = money(discount)
    total = subtotal - discount
    if discount < 0 or discount > subtotal:
        raise ValueError("El descuento debe estar entre $0 y el subtotal.")
    payment_amount = money(payment_amount)
    if payment_amount < 0 or payment_amount > total:
        raise ValueError("El pago inicial no puede ser negativo ni superar el total.")
    if total <= 0:
        raise ValueError("El total de la venta debe ser mayor que cero.")
    if payment_amount < total and not customer_name.strip():
        raise ValueError("Para una venta a crédito, registra el nombre del cliente.")

    with engine.begin() as conn:
        # Revalidar existencias dentro de la transacción.
        subtotal_check = Decimal("0.00")
        lines = []
        for pid, item in cart.items():
            p = conn.execute(select(products).where(products.c.id == int(pid), products.c.active == True)).mappings().first()
            if not p:
                raise ValueError(f"El producto {item['name']} ya no está disponible.")
            qty = int(item["qty"])
            if qty < 1 or int(p["stock"]) < qty:
                raise ValueError(f"Stock insuficiente para {p['name']}. Disponible: {p['stock']}.")
            price = money(item["price"])
            if price < 0:
                raise ValueError("El precio no puede ser negativo.")
            subtotal_check += price * qty
            lines.append((p, qty, price))
        total = subtotal_check - discount
        if payment_amount > total:
            raise ValueError("El pago supera el total actualizado.")
        balance = total - payment_amount
        status = "PAGADA" if balance == 0 else ("ABONO PARCIAL" if payment_amount > 0 else "PENDIENTE")
        folio = f"BF-{datetime.now():%y%m%d%H%M%S%f}"[-22:]
        sale_id = conn.execute(sales.insert().values(
            folio=folio, customer_id=customer_id, customer_name=customer_name.strip() or "Público general",
            sale_date=datetime.now(), subtotal=subtotal_check, discount=discount, total=total,
            paid_total=payment_amount, balance=balance, status=status, notes=notes
        )).inserted_primary_key[0]
        for p, qty, price in lines:
            conn.execute(sale_items.insert().values(
                sale_id=sale_id, product_id=p["id"], product_name=p["name"], quantity=qty,
                unit_price=price, unit_cost=money(p["cost_price"]), line_total=price * qty
            ))
            record_stock_movement(conn, p["id"], "VENTA", -qty, f"Venta {folio}")
        if payment_amount > 0:
            conn.execute(payments.insert().values(
                sale_id=sale_id, amount=payment_amount, method=payment_method,
                paid_at=datetime.now(), notes="Pago inicial"
            ))
    return folio, total, balance

# ---------------------------------------------------------------------
# Navegación móvil: menú de cuadros y botón de regreso
# ---------------------------------------------------------------------
PAGES = {
    "✨ Inicio": ("Inicio", "Resumen del negocio"),
    "🛍️ Nueva venta": ("Nueva venta", "Cobra productos y registra pagos"),
    "➕ Nuevo producto": ("Nuevo producto", "Registra una joya o accesorio"),
    "💎 Productos": ("Inventario", "Consulta existencias y precios"),
    "📥 Entrada de stock": ("Entrada de stock", "Registra mercancía recibida"),
    "👥 Clientes": ("Clientes", "Administra tus clientes"),
    "💳 Cuentas por cobrar": ("Cuentas por cobrar y abonos", "Selecciona una cuenta y registra abonos"),
    "📊 Reportes": ("Reportes", "Ventas y movimientos de inventario"),
    "⚙️ Administración": ("Administración", "Edita productos y exporta datos"),
}
if "bf_page" not in st.session_state:
    st.session_state.bf_page = "✨ Inicio"
page = st.session_state.bf_page

if page == "✨ Inicio":
    logo_path = "logo.png" if os.path.exists("logo.png") else ("logo.jpg" if os.path.exists("logo.jpg") else ("logo.jpeg" if os.path.exists("logo.jpeg") else None))
    if logo_path:
        st.markdown('<div class="bf-hero">', unsafe_allow_html=True)
        st.image(logo_path, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bf-hero"><div class="bf-brand" style="font-size:2rem">BENIFERCH</div><div class="bf-sub">JOYERÍA & ACCESORIOS</div></div>', unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;color:#c9c2b1;margin-bottom:18px'>¿Qué deseas hacer hoy?</div>", unsafe_allow_html=True)
    tile_data = [
        ("🛍️ Nueva venta", "🛍️", "Cobrar una venta"),
        ("➕ Nuevo producto", "➕", "Dar de alta un producto"),
        ("💎 Productos", "💎", "Consultar inventario"),
        ("📥 Entrada de stock", "📦", "Agregar existencias"),
        ("👥 Clientes", "👥", "Directorio de clientes"),
        ("💳 Cuentas por cobrar", "💳", "Selecciona una cuenta y aplica abonos"),
        ("📊 Reportes", "📊", "Consultar resultados"),
        ("⚙️ Administración", "⚙️", "Ajustes y exportaciones"),
    ]
    # Cuadros fluidos: 2 columnas en celular y 3 en pantallas amplias.
    cols_per_row = 2 if st.session_state.get("bf_mobile_layout", True) else 3
    for i in range(0, len(tile_data), cols_per_row):
        cols = st.columns(cols_per_row, gap="small")
        for col, item in zip(cols, tile_data[i:i+cols_per_row]):
            label, emoji, desc = item
            with col:
                st.markdown(f'<div class="bf-tile"><div class="bf-tile-icon">{emoji}</div><div class="bf-tile-title">{PAGES[label][0]}</div><div class="bf-tile-caption">{desc}</div></div>', unsafe_allow_html=True)
                if st.button(f"Abrir {PAGES[label][0]}", key=f"tile_{label}", use_container_width=True):
                    st.session_state.bf_page = label
                    st.rerun()
    st.divider()
else:
    back_col, title_col = st.columns([1, 5])
    with back_col:
        if st.button("← Inicio", use_container_width=True, key="back_home"):
            st.session_state.bf_page = "✨ Inicio"
            st.rerun()
    with title_col:
        st.markdown(f'<div class="bf-brand" style="font-size:1.25rem;padding-top:6px">BENIFERCH</div><div class="bf-sub">{PAGES[page][1]}</div>', unsafe_allow_html=True)

if CLOUD_DB:
    st.caption("● Base de datos alojada")
else:
    st.warning("Modo local: configura PostgreSQL antes de usar en la nube.")

st.title(page)

# ---------------------------------------------------------------------
# Inicio
# ---------------------------------------------------------------------
if page == "✨ Inicio":
    today = date.today().isoformat()
    summary = df_query("""
        SELECT
          COALESCE((SELECT SUM(total) FROM sales WHERE DATE(sale_date)=:today),0) AS sales_today,
          COALESCE((SELECT SUM(amount) FROM payments WHERE DATE(paid_at)=:today),0) AS collected_today,
          COALESCE((SELECT SUM(balance) FROM sales WHERE balance>0),0) AS receivable,
          COALESCE((SELECT SUM(stock*cost_price) FROM products WHERE active=TRUE),0) AS stock_value,
          COALESCE((SELECT SUM(stock) FROM products WHERE active=TRUE),0) AS units
    """, {"today": today}).iloc[0]
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Ventas de hoy", f"${float(summary.sales_today):,.2f}")
    c2.metric("Cobrado hoy", f"${float(summary.collected_today):,.2f}")
    c3.metric("Por cobrar", f"${float(summary.receivable):,.2f}")
    c4.metric("Unidades en stock", f"{int(summary.units):,}")
    st.caption(f"Valor de inventario a costo: ${float(summary.stock_value):,.2f}")
    a,b = st.columns(2)
    with a:
        st.subheader("⚠️ Existencias bajas")
        low = df_query("""SELECT name AS Producto, stock AS Stock, min_stock AS "Mínimo"
                          FROM products WHERE active=TRUE AND stock<=min_stock ORDER BY stock,name""")
        if low.empty:
            st.success("No hay productos debajo del stock mínimo.")
        else:
            st.dataframe(low, use_container_width=True, hide_index=True)
    with b:
        st.subheader("🧾 Ventas recientes")
        recent = df_query("""SELECT folio AS Folio, customer_name AS Cliente, sale_date AS Fecha,
                             total AS Total, balance AS Saldo, status AS Estado
                             FROM sales ORDER BY id DESC LIMIT 8""")
        if recent.empty:
            st.info("Todavía no hay ventas registradas.")
        else:
            st.dataframe(recent, use_container_width=True, hide_index=True)

elif page == "➕ Nuevo producto":
    st.subheader("➕ Registrar nuevo producto")
    st.caption("Completa los datos y pulsa Guardar producto. Los campos están acomodados en vertical para facilitar el uso desde celular.")
    with st.form("new_product", clear_on_submit=True):
        name = st.text_input("Nombre del producto *", placeholder="Ej. Aretes corazón")
        sku = st.text_input("Código / SKU (opcional)", placeholder="Ej. BF-001")
        category = st.selectbox("Categoría", ["Aretes", "Collares", "Pulseras", "Anillos", "Relojes", "Acero inoxidable", "Laminado en oro", "Otros"])
        material = st.text_input("Material o acabado", placeholder="Ej. Acero inoxidable dorado")
        cost = st.number_input("Costo unitario ($)", min_value=0.0, step=1.0, format="%.2f")
        price = st.number_input("Precio de venta ($)", min_value=0.0, step=1.0, format="%.2f")
        stock = st.number_input("Stock inicial", min_value=0, step=1, value=0)
        minimum = st.number_input("Avisar cuando llegue a", min_value=0, step=1, value=2)
        desc = st.text_area("Descripción (opcional)")
        submitted = st.form_submit_button("💾 Guardar producto", use_container_width=True, type="primary")
    if submitted:
        if not name.strip():
            st.error("El nombre del producto es obligatorio.")
        else:
            try:
                with engine.begin() as conn:
                    if sku.strip():
                        existing = conn.execute(select(products.c.id).where(products.c.sku == sku.strip())).first()
                        if existing:
                            st.error("Ese código SKU ya está registrado. Usa otro código o deja el campo vacío.")
                            st.stop()
                    result = conn.execute(products.insert().values(
                        sku=sku.strip() or None, name=name.strip(), category=category,
                        material=material.strip() or None, description=desc.strip() or None,
                        cost_price=money(cost), sale_price=money(price), stock=int(stock),
                        min_stock=int(minimum), active=True, created_at=datetime.now()
                    ))
                    pid = result.inserted_primary_key[0]
                    if stock:
                        conn.execute(stock_movements.insert().values(
                            product_id=pid, movement_type="STOCK INICIAL", quantity=int(stock),
                            stock_before=0, stock_after=int(stock), reason="Alta de producto",
                            created_at=datetime.now()
                        ))
                st.success(f"Producto '{name.strip()}' guardado correctamente.")
                st.rerun()
            except Exception as e:
                st.error("No se pudo guardar el producto. Revisa los datos y que el código SKU no esté repetido.")
                st.caption(str(e))


elif page == "💎 Productos":
    st.subheader("💎 Inventario de productos")
    query = st.text_input("Buscar producto por nombre, código o material", key="product_search")
    df = get_products(active_only=False)
    if not df.empty:
        df = df[df["active"] == True]
        if query:
            mask = df.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
            df = df[mask]
        view = df.rename(columns={
            "sku":"Código", "name":"Producto", "category":"Categoría", "material":"Material",
            "cost_price":"Costo", "sale_price":"Precio venta", "stock":"Stock", "min_stock":"Stock mínimo"
        })
        st.dataframe(view[["Código","Producto","Categoría","Material","Costo","Precio venta","Stock","Stock mínimo"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay productos registrados. Entra en «Nuevo producto» desde el inicio para agregar el primero.")

    st.divider()
    st.subheader("📦 Resumen de movimientos de inventario")
    st.caption("El inventario inicial se calcula al comienzo del periodo seleccionado; las ventas se restan, las entradas se suman y se compara con la existencia actual.")
    d1, d2 = st.columns(2)
    today = date.today()
    start_inv = d1.date_input("Desde", value=date(today.year, today.month, 1), key="inv_start")
    end_inv = d2.date_input("Hasta", value=today, key="inv_end")
    if start_inv > end_inv:
        st.error("La fecha inicial no puede ser posterior a la fecha final.")
    else:
        inv_products = get_products(active_only=False)
        inv_products = inv_products[inv_products["active"] == True] if not inv_products.empty else inv_products
        mov = df_query("""SELECT product_id, movement_type, quantity FROM stock_movements
                          WHERE DATE(created_at)>=:start AND DATE(created_at)<=:end""",
                       {"start": start_inv.isoformat(), "end": end_inv.isoformat()})
        rows = []
        for _, pr in inv_products.iterrows():
            pm = mov[mov["product_id"] == pr["id"]] if not mov.empty else pd.DataFrame()
            sold = int(-pm.loc[pm["movement_type"] == "VENTA", "quantity"].sum()) if not pm.empty else 0
            entries = int(pm.loc[pm["movement_type"] == "ENTRADA", "quantity"].sum()) if not pm.empty else 0
            current = int(pr["stock"])
            opening = current + sold - entries
            rows.append({"Producto": pr["name"], "Inventario inicial": opening,
                         "Menos ventas": sold, "Entradas de stock": entries,
                         "Inventario final": current})
        inv_df = pd.DataFrame(rows, columns=["Producto", "Inventario inicial", "Menos ventas", "Entradas de stock", "Inventario final"])
        if inv_df.empty:
            st.info("No hay productos para mostrar.")
        else:
            st.dataframe(inv_df, use_container_width=True, hide_index=True)
            totals = {c: int(inv_df[c].sum()) for c in ["Inventario inicial", "Menos ventas", "Entradas de stock", "Inventario final"]}
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("Inicial", totals["Inventario inicial"])
            m2.metric("Ventas", f'-{totals["Menos ventas"]}')
            m3.metric("Entradas", f'+{totals["Entradas de stock"]}')
            m4.metric("Final", totals["Inventario final"])
            st.download_button("Descargar resumen de inventario CSV", inv_df.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"beniferch_inventario_{start_inv}_{end_inv}.csv", mime="text/csv")

# Nueva venta
# ---------------------------------------------------------------------
elif page == "🛍️ Nueva venta":
    dfp = get_products()
    if dfp.empty:
        st.warning("Primero registra productos con existencias.")
    else:
        if "cart" not in st.session_state:
            st.session_state.cart = {}
        st.subheader("1. Agrega productos al carrito")
        product_ids = dfp["id"].tolist()
        selected = st.selectbox("Producto", product_ids, format_func=lambda pid: (
            f"{dfp.loc[dfp.id==pid,'name'].iloc[0]} · Stock {int(dfp.loc[dfp.id==pid,'stock'].iloc[0])} · "
            f"${float(dfp.loc[dfp.id==pid,'sale_price'].iloc[0]):,.2f}"
        ))
        selected_row = dfp[dfp.id == selected].iloc[0]
        colq, colp, colb = st.columns([1,1,1])
        qty = colq.number_input("Cantidad", min_value=1, max_value=max(1,int(selected_row.stock)), value=1, step=1)
        price = colp.number_input("Precio unitario ($)", min_value=0.0, value=float(selected_row.sale_price), step=1.0, format="%.2f")
        if colb.button("Añadir al carrito", use_container_width=True):
            if selected in st.session_state.cart:
                new_qty = st.session_state.cart[selected]["qty"] + int(qty)
            else:
                new_qty = int(qty)
            if new_qty > int(selected_row.stock):
                st.error(f"Solo hay {int(selected_row.stock)} unidades disponibles.")
            else:
                st.session_state.cart[selected] = {
                    "name": selected_row["name"], "qty": new_qty, "price": money(price),
                    "stock": int(selected_row.stock)
                }
                st.rerun()
        cart = st.session_state.cart
        st.subheader("2. Revisa la venta")
        if cart:
            cart_df = pd.DataFrame([{
                "Producto": v["name"], "Cantidad": v["qty"], "Precio": float(v["price"]),
                "Importe": float(v["price"])*v["qty"], "Disponible": v["stock"]
            } for v in cart.values()])
            st.dataframe(cart_df, use_container_width=True, hide_index=True)
            colrm1,colrm2 = st.columns([2,1])
            remove_id = colrm1.selectbox("Quitar un producto", list(cart.keys()), format_func=lambda pid: cart[pid]["name"])
            if colrm2.button("Quitar", use_container_width=True):
                del st.session_state.cart[remove_id]
                st.rerun()
            subtotal = sum((money(v["price"])*v["qty"] for v in cart.values()), Decimal("0.00"))
            with st.form("checkout"):
                col1,col2 = st.columns(2)
                customer_df = get_customers()
                customer_choice = col1.selectbox("Cliente (opcional)", ["Público general"] + [
                    f"{int(r.id)} · {r.name}" for r in customer_df.itertuples()
                ])
                customer_name = "Público general"
                customer_id = None
                if customer_choice != "Público general":
                    customer_id = int(customer_choice.split(" · ",1)[0])
                    customer_name = customer_choice.split(" · ",1)[1]
                discount = col2.number_input("Descuento total ($)", min_value=0.0, max_value=float(subtotal), value=0.0, step=1.0)
                total = subtotal - money(discount)
                st.markdown(f"### Total: ${float(total):,.2f}")
                payment_amount = st.number_input("Pago recibido ahora ($)", min_value=0.0, max_value=float(total), value=float(total), step=1.0, format="%.2f")
                method = st.selectbox("Método de pago", ["Efectivo","Transferencia","Tarjeta","Otro"])
                notes = st.text_input("Notas (opcional)")
                submit = st.form_submit_button("Confirmar venta", use_container_width=True)
            if submit:
                try:
                    folio, total_saved, balance = create_sale(
                        customer_name, customer_id, cart, discount, payment_amount, method, notes
                    )
                    st.session_state.cart = {}
                    st.success(f"Venta {folio} registrada. Total ${float(total_saved):,.2f}; saldo ${float(balance):,.2f}.")
                    st.rerun()
                except (ValueError, SQLAlchemyError) as e:
                    st.error(str(e))
        else:
            st.info("Tu carrito está vacío.")

# ---------------------------------------------------------------------
# Entradas de stock
# ---------------------------------------------------------------------
elif page == "📥 Entrada de stock":
    dfp = get_products()
    if dfp.empty:
        st.info("Registra primero un producto.")
    else:
        with st.form("stock_entry"):
            pid = st.selectbox("Producto", dfp.id.tolist(), format_func=lambda x: (
                f"{dfp.loc[dfp.id==x,'name'].iloc[0]} · Stock actual {int(dfp.loc[dfp.id==x,'stock'].iloc[0])}"
            ))
            qty = st.number_input("Cantidad que ingresa", min_value=1, value=1, step=1)
            reason = st.text_input("Motivo", value="Resurtido")
            submitted = st.form_submit_button("Registrar entrada", use_container_width=True)
        if submitted:
            try:
                with engine.begin() as conn:
                    record_stock_movement(conn, pid, "ENTRADA", int(qty), reason.strip() or "Resurtido")
                st.success("Entrada registrada.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

# ---------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------
elif page == "👥 Clientes":
    tab1,tab2 = st.tabs(["Directorio","Nuevo cliente"])
    with tab1:
        d = get_customers()
        if d.empty:
            st.info("Todavía no hay clientes registrados.")
        else:
            st.dataframe(d.rename(columns={"id":"ID","name":"Cliente","phone":"Teléfono"}) , use_container_width=True, hide_index=True)
    with tab2:
        with st.form("new_customer", clear_on_submit=True):
            cname = st.text_input("Nombre completo *")
            phone = st.text_input("Teléfono")
            notes = st.text_area("Notas")
            submit = st.form_submit_button("Guardar cliente", use_container_width=True)
        if submit:
            if not cname.strip():
                st.error("El nombre es obligatorio.")
            else:
                with engine.begin() as conn:
                    conn.execute(customers.insert().values(
                        name=cname.strip(), phone=phone.strip() or None,
                        notes=notes.strip() or None, created_at=datetime.now()
                    ))
                st.success("Cliente guardado.")
                st.rerun()

# ---------------------------------------------------------------------
# Cuentas por cobrar y abonos
# ---------------------------------------------------------------------
elif page == "💳 Cuentas por cobrar":
    st.subheader("💳 Cuentas por cobrar y abonos")
    st.caption("Selecciona una cuenta pendiente para revisar el saldo y registrar un abono. El pago se descuenta automáticamente del saldo.")
    df = df_query("""SELECT id, folio, customer_name AS cliente, sale_date AS fecha,
                            total, paid_total AS abonado, balance AS saldo, status AS estado
                     FROM sales WHERE balance > 0 ORDER BY sale_date""")
    if df.empty:
        st.success("¡No hay cuentas pendientes por cobrar!")
    else:
        st.dataframe(df.rename(columns={"id":"ID","folio":"Folio","cliente":"Cliente","fecha":"Fecha",
                      "total":"Total","abonado":"Abonado","saldo":"Saldo","estado":"Estado"}),
                     use_container_width=True, hide_index=True)
        sale_id = st.selectbox("Selecciona la cuenta a la que aplicarás el abono", df.id.tolist(), key="combined_sale_select",
            format_func=lambda x: (f"{df.loc[df.id==x,'folio'].iloc[0]} · {df.loc[df.id==x,'cliente'].iloc[0]} · Saldo ${float(df.loc[df.id==x,'saldo'].iloc[0]):,.2f}"))
        current = money(df.loc[df.id==sale_id,"saldo"].iloc[0])
        st.metric("Saldo pendiente de la cuenta seleccionada", f"${float(current):,.2f}")
        with st.form("combined_payment_form", clear_on_submit=True):
            amount = st.number_input("Importe del abono ($)", min_value=0.01, max_value=float(current),
                                     value=float(current), step=1.0, format="%.2f")
            method = st.selectbox("Método de pago", ["Efectivo","Transferencia","Tarjeta","Otro"])
            notes = st.text_input("Nota del abono (opcional)")
            submit = st.form_submit_button("💵 Aplicar abono", use_container_width=True, type="primary")
        if submit:
            try:
                amount_d = money(amount)
                with engine.begin() as conn:
                    sale = conn.execute(select(sales).where(sales.c.id == int(sale_id))).mappings().first()
                    if not sale or money(sale["balance"]) <= 0:
                        raise ValueError("Esta cuenta ya está liquidada.")
                    if amount_d <= 0 or amount_d > money(sale["balance"]):
                        raise ValueError(f"El abono debe ser mayor que $0 y no superar ${money(sale['balance']):,.2f}.")
                    new_paid = money(sale["paid_total"]) + amount_d
                    new_balance = money(sale["total"]) - new_paid
                    status = "PAGADA" if new_balance == 0 else "ABONO PARCIAL"
                    conn.execute(payments.insert().values(sale_id=int(sale_id), amount=amount_d,
                        method=method, paid_at=datetime.now(), notes=notes.strip() or None))
                    conn.execute(sales.update().where(sales.c.id == int(sale_id)).values(
                        paid_total=new_paid, balance=new_balance, status=status))
                st.success(f"Abono de ${float(amount_d):,.2f} aplicado. Nuevo saldo: ${float(new_balance):,.2f}.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    st.divider()
    st.subheader("🧾 Historial de pagos y abonos")
    hist = df_query("""SELECT p.paid_at AS Fecha, s.folio AS Folio, s.customer_name AS Cliente,
                              p.amount AS Importe, p.method AS Método, p.notes AS Nota
                       FROM payments p JOIN sales s ON s.id=p.sale_id ORDER BY p.id DESC LIMIT 100""")
    if hist.empty:
        st.info("Todavía no hay pagos registrados.")
    else:
        st.dataframe(hist, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------
elif page == "📊 Reportes":
    col1,col2 = st.columns(2)
    start = col1.date_input("Desde", value=date(date.today().year,date.today().month,1))
    end = col2.date_input("Hasta", value=date.today())
    if start > end:
        st.error("La fecha inicial no puede ser posterior a la final.")
    else:
        df = df_query("""SELECT folio AS Folio, sale_date AS Fecha, customer_name AS Cliente,
                                total AS Total, paid_total AS Cobrado, balance AS Pendiente, status AS Estado
                         FROM sales WHERE DATE(sale_date)>=:start AND DATE(sale_date)<=:end
                         ORDER BY sale_date DESC""", {"start":start.isoformat(),"end":end.isoformat()})
        total_sales = float(df["Total"].sum()) if not df.empty else 0
        total_paid = float(df["Cobrado"].sum()) if not df.empty else 0
        total_due = float(df["Pendiente"].sum()) if not df.empty else 0
        c1,c2,c3 = st.columns(3)
        c1.metric("Ventas del periodo", f"${total_sales:,.2f}")
        c2.metric("Pagos aplicados a esas ventas", f"${total_paid:,.2f}")
        c3.metric("Saldo de esas ventas", f"${total_due:,.2f}")
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("Descargar ventas CSV", df.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"beniferch_ventas_{start}_{end}.csv", mime="text/csv")
        else:
            st.info("No hay ventas en el periodo seleccionado.")
        movements = df_query("""SELECT sm.created_at AS Fecha, p.name AS Producto,
                                       sm.movement_type AS Movimiento, sm.quantity AS Cantidad,
                                       sm.stock_before AS "Antes", sm.stock_after AS "Después",
                                       sm.reason AS Motivo
                                FROM stock_movements sm JOIN products p ON p.id=sm.product_id
                                WHERE DATE(sm.created_at)>=:start AND DATE(sm.created_at)<=:end
                                ORDER BY sm.created_at DESC""", {"start":start.isoformat(),"end":end.isoformat()})
        st.subheader("Movimientos de inventario")
        st.dataframe(movements, use_container_width=True, hide_index=True)
        if not movements.empty:
            st.download_button("Descargar movimientos CSV", movements.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"beniferch_movimientos_{start}_{end}.csv", mime="text/csv")

# ---------------------------------------------------------------------
# Administración
# ---------------------------------------------------------------------
elif page == "⚙️ Administración":
    st.subheader("Editar producto")
    df = get_products(active_only=False)
    if not df.empty:
        pid = st.selectbox("Selecciona un producto", df.id.tolist(), format_func=lambda x: (
            f"{df.loc[df.id==x,'name'].iloc[0]} (ID {x})"
        ))
        row = df[df.id==pid].iloc[0]
        with st.form("edit_product"):
            name = st.text_input("Nombre", value=str(row["name"]))
            sku = st.text_input("Código SKU", value="" if pd.isna(row["sku"]) else str(row["sku"]))
            category = st.text_input("Categoría", value=str(row["category"]))
            material = st.text_input("Material", value="" if pd.isna(row["material"]) else str(row["material"]))
            cost = st.number_input("Costo", min_value=0.0, value=float(row["cost_price"]), format="%.2f")
            price = st.number_input("Precio de venta", min_value=0.0, value=float(row["sale_price"]), format="%.2f")
            minimum = st.number_input("Stock mínimo", min_value=0, value=int(row["min_stock"]))
            active = st.checkbox("Producto activo", value=bool(row["active"]))
            save = st.form_submit_button("Guardar cambios", use_container_width=True)
        if save:
            if not name.strip():
                st.error("El nombre no puede estar vacío.")
            else:
                try:
                    with engine.begin() as conn:
                        conn.execute(products.update().where(products.c.id==int(pid)).values(
                            name=name.strip(), sku=sku.strip() or None, category=category.strip() or "Otros",
                            material=material.strip() or None, cost_price=money(cost), sale_price=money(price),
                            min_stock=int(minimum), active=active
                        ))
                    st.success("Producto actualizado.")
                    st.rerun()
                except Exception:
                    st.error("No se pudo guardar. Revisa que el SKU no esté duplicado.")
        st.warning("Los productos con historial de ventas se desactivan; no se eliminan para conservar los reportes.")
    else:
        st.info("No hay productos registrados.")
    st.divider()
    st.subheader("Exportar datos")
    for table_name, filename in [
        ("products","beniferch_productos.csv"), ("sales","beniferch_ventas_completas.csv"),
        ("payments","beniferch_pagos.csv"), ("stock_movements","beniferch_movimientos.csv"),
        ("customers","beniferch_clientes.csv")
    ]:
        try:
            data = df_query(f"SELECT * FROM {table_name} ORDER BY id DESC")
            st.download_button(f"Descargar {table_name}", data.to_csv(index=False).encode("utf-8-sig"),
                               file_name=filename, mime="text/csv", key=f"export_{table_name}")
        except Exception:
            st.caption(f"No se pudo preparar la exportación de {table_name}.")

st.caption("BeniFerch · Gestión de joyería y accesorios")
