import os
import asyncio, sqlite3, logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


TOKEN = os.getenv("8656865785:AAE-2mZ1nwIk7SQdNVeotVuSSzCSakeY8KU")
bot = Bot(token=TOKEN)

PRICE_PER_KV = 100000
FEE = 1.10 


class Flow(StatesGroup):
    role, name, city, phone = State(), State(), State(), State()
    obj_type, area, exact_address, choosing_date, choosing_time = State(), State(), State(), State(), State()
    edit_name, edit_city = State(), State()

def db_query(q, p=(), fetch=False, return_id=False):
    with sqlite3.connect("pro_clean.db") as conn:
        cursor = conn.cursor()
        cursor.execute(q, p)
        if return_id: return cursor.lastrowid
        res = cursor.fetchone() if fetch and "SELECT" in q and "LIMIT 1" in q or "uid=?" in q else (cursor.fetchall() if fetch else None)
        conn.commit()
        return res

# Jadvallar
db_query("CREATE TABLE IF NOT EXISTS users (uid INTEGER PRIMARY KEY, role TEXT, name TEXT, city TEXT, phone TEXT)")
db_query("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, cid INTEGER, obj TEXT, area TEXT, addr TEXT, time TEXT, price REAL, status TEXT DEFAULT 'pending')")

def get_main_kb(uid):
    u = db_query("SELECT role FROM users WHERE uid=?", (uid,), True)
    if not u: return None
    role = u[0]
    kb = ReplyKeyboardBuilder()
    if role == 'client':
        kb.button(text="E'lon berish ➕")
    else:
        kb.button(text="Ochiq e'lonlar 📂")
    kb.button(text="Profil 👤")
    return kb.adjust(1).as_markup(resize_keyboard=True)

router = Router()

@router.message(CommandStart())
async def start(m: types.Message, state: FSMContext):
    await state.clear()
    u = db_query("SELECT role FROM users WHERE uid=?", (m.from_user.id,), True)
    if u:
        await m.answer("Asosiy menyu:", reply_markup=get_main_kb(m.from_user.id))
    else:
        ikb = InlineKeyboardBuilder().button(text="🏠 Mijoz", callback_data="r_client").button(text="🧹 Ishchi", callback_data="r_worker")
        await m.answer("Xush kelibsiz! Rolingizni tanlang:", reply_markup=ikb.as_markup())
        await state.set_state(Flow.role)

@router.callback_query(Flow.role)
async def set_r(c: types.CallbackQuery, state: FSMContext):
    role = c.data.split("_")[1]
    await state.update_data(role=role)
    await c.message.answer("Ismingizni kiriting:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Flow.name)

@router.message(Flow.name)
async def set_n(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    kb = ReplyKeyboardBuilder()
    for city in ["Toshkent", "Farg'ona", "Namangan"]: kb.button(text=city)
    await m.answer("Shaharni tanlang:", reply_markup=kb.as_markup(resize_keyboard=True))
    await state.set_state(Flow.city)

@router.message(Flow.city)
async def set_c(m: types.Message, state: FSMContext):
    await state.update_data(city=m.text)
    await m.answer("📞 Raqamingizni yuboring:", reply_markup=ReplyKeyboardBuilder().button(text="Kontaktni ulashish", request_contact=True).as_markup(resize_keyboard=True))
    await state.set_state(Flow.phone)

@router.message(Flow.phone, F.contact)
async def set_p(m: types.Message, state: FSMContext):
    d = await state.get_data()
    db_query("INSERT OR REPLACE INTO users (uid, role, name, city, phone) VALUES (?,?,?,?,?)", (m.from_user.id, d['role'], d['name'], d['city'], m.contact.phone_number))
    await m.answer("✅ Ro'yxatdan o'tdingiz!", reply_markup=get_main_kb(m.from_user.id))
    await state.clear()

# --- PROFIL FUNKSIYASI ---
@router.message(F.text == "Profil 👤")
async def show_profile(m: types.Message):
    u = db_query("SELECT role, name, city, phone FROM users WHERE uid=?", (m.from_user.id,), True)
    if not u: return
    role, name, city, phone = u
    role_text = "Mijoz 🏠" if role == 'client' else "Ishchi 🧹"
    text = f"🪪 Ma'lumotlaringiz:\n\n👤 Ism: {name}\n📍 Shahar: {city}\n📞 Tel: {phone}\n🛠 Rol: {role_text}"
    
    ikb = InlineKeyboardBuilder()
    ikb.button(text="Ismni o'zgartirish ✏️", callback_data="edit_name")
    ikb.button(text="Shaharni o'zgartirish 📍", callback_data="edit_city")
    ikb.button(text="Chiqish 🚪", callback_data="logout")
    await m.answer(text, reply_markup=ikb.adjust(1).as_markup())

@router.callback_query(F.data == "edit_name")
async def edit_n(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Yangi ismni kiriting:")
    await state.set_state(Flow.edit_name)

@router.message(Flow.edit_name)
async def edit_n_done(m: types.Message, state: FSMContext):
    db_query("UPDATE users SET name=? WHERE uid=?", (m.text, m.from_user.id))
    await m.answer("✅ Ism yangilandi!", reply_markup=get_main_kb(m.from_user.id))
    await state.clear()

@router.callback_query(F.data == "edit_city")
async def edit_c(c: types.CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardBuilder()
    for city in ["Toshkent", "Farg'ona", "Namangan"]: kb.button(text=city)
    await c.message.answer("Yangi shaharni tanlang:", reply_markup=kb.as_markup(resize_keyboard=True))
    await state.set_state(Flow.edit_city)

@router.message(Flow.edit_city)
async def edit_c_done(m: types.Message, state: FSMContext):
    db_query("UPDATE users SET city=? WHERE uid=?", (m.text, m.from_user.id))
    await m.answer("✅ Shahar yangilandi!", reply_markup=get_main_kb(m.from_user.id))
    await state.clear()

@router.callback_query(F.data == "logout")
async def logout(c: types.CallbackQuery):
    db_query("DELETE FROM users WHERE uid=?", (c.from_user.id,))
    await c.message.answer("🚪 Profilingiz o'chirildi. Qayta ro'yxatdan o'tish uchun /start")

# --- ORDER JARAYONI ---
@router.message(F.text == "E'lon berish ➕")
async def start_order(m: types.Message, state: FSMContext):
    ikb = InlineKeyboardBuilder().button(text="🏠 Uy", callback_data="obj_Uy").button(text="🏢 Ofis", callback_data="obj_Ofis")
    await m.answer("Obyekt turini tanlang:", reply_markup=ikb.as_markup())
    await state.set_state(Flow.obj_type)

@router.callback_query(Flow.obj_type)
async def set_obj(c: types.CallbackQuery, state: FSMContext):
    await state.update_data(obj_type=c.data.split("_")[1])
    await c.message.answer("Maydonni kiriting (kv/m):")
    await state.set_state(Flow.area)

@router.message(Flow.area)
async def set_area(m: types.Message, state: FSMContext):
    if not m.text.isdigit(): return await m.answer("Faqat raqam kiriting!")
    await state.update_data(area=m.text)
    await m.answer("Aniq manzilni yozing:")
    await state.set_state(Flow.exact_address)

@router.message(Flow.exact_address)
async def set_addr(m: types.Message, state: FSMContext):
    await state.update_data(exact_address=m.text)
    ikb = InlineKeyboardBuilder()
    for i in range(5):
        dt = (datetime.now() + timedelta(days=i)).strftime("%d-%m")
        ikb.button(text=dt, callback_data=f"date_{dt}")
    await m.answer("Kunni tanlang:", reply_markup=ikb.adjust(2).as_markup())
    await state.set_state(Flow.choosing_date)

@router.callback_query(Flow.choosing_date)
async def set_date(c: types.CallbackQuery, state: FSMContext):
    await state.update_data(date=c.data.split("_")[1])
    ikb = InlineKeyboardBuilder()
    for h in ["09:00", "12:00", "15:00", "18:00"]: ikb.button(text=h, callback_data=f"time_{h}")
    await c.message.edit_text("Soatni tanlang:", reply_markup=ikb.as_markup())
    await state.set_state(Flow.choosing_time)

@router.callback_query(Flow.choosing_time)
async def finalize(c: types.CallbackQuery, state: FSMContext):
    time_val = c.data.split("_")[1]
    d = await state.get_data()
    price = int(d['area']) * PRICE_PER_KV * FEE
    f_time = f"{d['date']} {time_val}"
    
    oid = db_query("INSERT INTO orders (cid, obj, area, addr, time, price) VALUES (?,?,?,?,?,?)", 
                   (c.from_user.id, d['obj_type'], d['area'], d['exact_address'], f_time, price), return_id=True)
    
    u_city = db_query("SELECT city FROM users WHERE uid=?", (c.from_user.id,), True)[0]
    ws = db_query("SELECT uid FROM users WHERE role='worker' AND city=?", (u_city,), True)
    
    for w in ws:
        try:
            ikb = InlineKeyboardBuilder().button(text="✅ Qabul qilish", callback_data=f"accept_{oid}")
            await c.bot.send_message(w[0], f"🔔 Yangi e'lon! ({u_city})\n📍 {d['exact_address']}\n💰 {price:,.0f} so'm\n📅 {f_time}")
        except: pass
        
    await c.message.edit_text(f"✅ E'lon yuborildi!\n💰 Narxi: {price:,.0f} so'm")
    await state.clear()

@router.message(F.text == "Ochiq e'lonlar 📂")
async def show_orders(m: types.Message):
    u = db_query("SELECT city FROM users WHERE uid=?", (m.from_user.id,), True)
    if not u: return
    city = u[0]
    orders = db_query("SELECT id, addr, price, time FROM orders WHERE status='pending' AND cid IN (SELECT uid FROM users WHERE city=?)", (city,), True)
    if not orders: return await m.answer("Hozircha bo'sh e'lonlar yo'q.")
    for o in orders:
        ikb = InlineKeyboardBuilder().button(text="✅ Qabul qilish", callback_data=f"accept_{o[0]}")
        await m.answer(f"🆔 ID: {o[0]}\n📍 {o[1]}\n💰 {o[2]:,.0f} so'm\n📅 {o[3]}", reply_markup=ikb.as_markup())

@router.callback_query(F.data.startswith("accept_"))
async def accept(c: types.CallbackQuery):
    oid = c.data.split("_")[1]
    order = db_query("SELECT o.status, o.cid, o.price, o.addr, o.time, u.name, u.phone FROM orders o JOIN users u ON o.cid = u.uid WHERE o.id=?", (oid,), True)
    
    if order and order[0] == 'pending':
        st, cid, price, addr, o_time, c_name, c_phone = order
        db_query("UPDATE orders SET status='accepted' WHERE id=?", (oid,))
        w = db_query("SELECT name, phone FROM users WHERE uid=?", (c.from_user.id,), True)
        
        try: await c.bot.send_message(cid, f"✅ Buyurtmangiz qabul qilindi!\n👷 Ishchi: {w[0]}\n📞 Tel: {w[1]}\n💰 Narx: {price:,.0f}")
        except: pass
        
        await c.message.edit_text(f"🎉 Qabul qilindi!\n👤 Mijoz: {c_name}\n📞 Tel: {c_phone}\n📍 {addr}\n📅 {o_time}\n💰 {price:,.0f}")
    else:
        await c.answer("E'lon allaqachon olingan!", show_alert=True)

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
