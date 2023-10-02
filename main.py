from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.message import ContentTypes
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
import random

from db import Database
import config as cfg
import kb

db = Database("database.db")

client = Bot(token=cfg.TOKEN)
dp = Dispatcher(client, storage=MemoryStorage())

class ProfileStatesGroup(StatesGroup):
    answer = State()
    answer_to_answer = State()
    sending_load_photo = State()
    sending_load_text = State()
    test_send_post = State()
    
@dp.message_handler(content_types=["photo"], state=ProfileStatesGroup.sending_load_photo)
async def sending_load_photo_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['sending_photo'] = message.photo[0].file_id

    await message.answer('Текст рассылки:', reply_markup=kb.publ_markup)
    await ProfileStatesGroup.next()

@dp.message_handler(content_types=["text"], state=ProfileStatesGroup.sending_load_text)
async def sending_load_photo_and_text_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['sending_text'] = message.text

    await message.answer('ℹ️ Рассылка начата...')

    ids = db.get_all_id()
    for i in ids:
        await client.send_photo(i[0], data['sending_photo'], f'{data["sending_text"]}')
            
    await message.answer('✅ Рассылка закончена.')
    await state.finish()

@dp.message_handler(content_types=['text'], state=ProfileStatesGroup.answer)
async def answer_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        global answer
        answer = message.text
        data['answer'] = message.text
        global one_id
        one_id = message.from_user.id
    
    await message.answer(f'✅ *Готово, твое сообщение отправлено!*\n\nА если ты тоже хочешь получать анонимные послания от своих друзей, размести в инстаграме свою персональную ссылку.\n\n🔗 *Твоя ссылка:* https://t.me/{cfg.BOT_NAME}?start={message.from_user.id}', parse_mode='markdown', reply_markup=kb.chavo_markup)
    await client.send_message(referrer_id, f'✨ *У тебя новое анонимное послание:* (#{random.randint(1000000, 9999999)})\n\n{data["answer"]}', parse_mode='markdown', reply_markup=kb.answer_markup)
    await state.finish()

@dp.message_handler(content_types=['text'], state=ProfileStatesGroup.answer_to_answer)
async def answer_to_answer_state(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['answer_to_answer'] = message.text
    
    await client.send_message(one_id, f'✨ *Ты получил ответ на свое анонимное сообщение:* (#{random.randint(1000000, 9999999)})\n\n{data["answer_to_answer"]}', parse_mode='markdown')
    await message.answer('✌️ *Готово!* Твой ответ на анонимное послание успешно доставлен', parse_mode='markdown')
    await state.finish()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    db.create_table()
    if not db.user_exists(message.from_user.id):
        db.add_user(message.from_user.id)
        
    start_command = message.text
    global referrer_id
    referrer_id = str(start_command[7:])
    if referrer_id != '':
        if str(referrer_id) == str(message.from_user.id):
            await message.answer('❌ Нельзя отправлять валентинку самому себе!')
            return
        else:
            await message.answer('✨ Здесь ты можешь анонимно рассказать о своих чувствах к человеку, который опубликовал эту ссылку.\n\nНапиши сюда всё, что о нем думаешь в одном сообщении и через несколько мгновений он его получит, но не будет знать от кого оно.\n\n📌 *Для того чтобы получить свою личную ссылку - сначала напиши что нибудь!*', parse_mode='markdown')
            await ProfileStatesGroup.answer.set()
            return

    await message.answer(f'😉 *Привет!* Для того чтобы получать анонимные послания от своих друзей, просто размести свою личную ссылку в Инстаграм сторис или отправь его в чат с друзьями.\n\n🔗 *Твоя ссылка:* https://t.me/{cfg.BOT_NAME}?start={message.from_user.id}', parse_mode='markdown')

@dp.message_handler(commands=['apanel'])
async def apanel(message: types.Message):
    if message.from_user.id in cfg.ADMIN_ID:
        await message.answer(f'🤖 *Админ-панель*\n\nЗарегано людей: *{all_users_count()}*', parse_mode='markdown', reply_markup=kb.admin_markup)
    else:
        await message.answer('❌ *Ты не Администратор!*', parse_mode='markdown')
    
@dp.callback_query_handler(state = '*')
async def callback_query(call: types.CallbackQuery, state: FSMContext):
    if call.data == 'answer':
        await client.edit_message_text(f'✨ *У тебя новое анонимное послание:* (#{random.randint(1000000, 9999999)})\n\n{answer}', call.message.chat.id, call.message.message_id, parse_mode='markdown')
        await call.message.answer('⚡️ *Напиши ответ на анонимное послание одним сообщением...*', parse_mode='markdown')
        await ProfileStatesGroup.answer_to_answer.set()
    elif call.data == 'sending':
        await call.message.answer('Загрузи картинку:', reply_markup=kb.publ_markup)
        await ProfileStatesGroup.sending_load_photo.set()
    elif call.data == 'publ':
        await state.finish()
        await client.edit_message_text('ℹ️ Публикация отменена.', call.message.chat.id, call.message.message_id)

@dp.message_handler()
async def get_message(message: types.Message):
    await start(message)

def all_users_count():
    count = 0
    all_users = db.get_all_id()
    for _ in all_users:
        count += 1
    return count

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)