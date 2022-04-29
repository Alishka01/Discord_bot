import discord
from discord.ext import commands
import sqlite3
import string
from translate import Translator


bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot.remove_command('help')
TOKEN = "OTY2NzEzNDg0OTQ5NzI5MzUx.YmFwFw.yvaiO55eG51ug_5pDIDhs-KoEME"


@bot.event  # Подключение бота
async def on_ready():
    print(f'{str(bot.user)[:-5]} подключен к Discord...')

    global base, cursor
    base = sqlite3.connect("БД админского бота.db")
    cursor = base.cursor()
    if base:
        print("База данных подключена...")


@bot.event  # Проверка на нецензурные сообщения
async def on_message(message):
    if {word.lower().translate(str.maketrans('', '', string.punctuation)) for word in message.content.split(' ')} \
            .intersection(open("cenz_message", 'r', encoding='utf-8').read().split()) != set():
        await message.channel.send(f'{message.author.mention}, ууу... еще немного и БАН!!!')
        await message.delete()

        name = message.guild.name
        base.execute('CREATE TABLE IF NOT EXISTS {}(user_id INT, count INT)'.format(name))
        base.commit()

        warning = cursor.execute('SELECT * FROM {} WHERE user_id == ?'.format(name), (message.author.id,)).fetchone()

        if warning is None:
            cursor.execute('INSERT INTO {} VALUES(?, ?)'.format(name), (message.author.id, 1))
            base.commit()
            await message.channel.send(f'{message.author.mention}, 1-ое предупреждение. На 3-е - БАН!!!')
        elif warning[1] == 0:
            cursor.execute('UPDATE {} SET count == ? WHERE user_id == ?'.format(name), (1, message.author.id))
            base.commit()
            await message.channel.send(f'{message.author.mention}, уже 1-ое предупреждение. Бан близко!!!')
        elif warning[1] == 1:
            cursor.execute('UPDATE {} SET count == ? WHERE user_id == ?'.format(name), (2, message.author.id))
            base.commit()
            await message.channel.send(f'{message.author.mention}, уже 2-ое предупреждение. Бан близко!!!')
        elif warning[1] == 2:
            cursor.execute('UPDATE {} SET count == ? WHERE user_id == ?'.format(name), (0, message.author.id))
            base.commit()
            await message.channel.send(f'{message.author.mention}, а вот и всё. Бан за мат в чате.')
            await message.author.ban(reason='Нецензурные выражение')

    await bot.process_commands(message)


@bot.event  # Присоединение нового пользовотеля на сервер
async def on_member_join(member):
    await member.send(f'Привет,{member}. Я админский бот, слежу за порядком в чате, для просмотра команд '
                      f'пиши: "!инфо".\n'
                      f'Cпасибо, что присоединился к нам.')
    for chat in bot.get_guild(member.guild.id).channels:
        if chat.name == 'general':
            await bot.get_channel(chat.id).send(f'{member}, рады, что ты с нами, в лс инфо.')


@bot.event  # Выход пользователя с сервера
async def on_member_remove(member):
    for chat in bot.get_guild(member.guild.id).channels:
        if chat.name == 'general':
            await bot.get_channel(chat.id).send(f'{member}, пока. Будем скучать.')


@bot.command()  # Статус пользователя (количество предупреждений)
async def статус(ctx):
    base.execute('CREATE TABLE IF NOT EXISTS {}(user_id INT, count INT)'.format(ctx.message.guild.name))
    base.commit()
    warning = cursor.execute('SELECT * FROM {} WHERE user_id == ?'.format(ctx.message.guild.name),
                             (ctx.message.author.id,)).fetchone()

    if warning is None:
        await ctx.send(f'{ctx.message.author.mention}, у вас пока нет предупреждений.')
    else:
        await ctx.send(f'{ctx.message.author.mention}, у вас предупреждений: {warning[1]}.')


@bot.command()  # Инфо о боте
async def инфо(ctx, arg=None):
    author = ctx.message.author.mention
    if arg is None:
        await ctx.send(f'{author} Введите:\n !инфо общая \n !инфо команды')
    elif arg == "общая":
        await ctx.send(f'{author} Я админский бот, слежу за порядком в чате. БАН - за 3 предупреждения за мат.')
    elif arg == "команды":
        await ctx.send(f'{author} {open("commands", "r", encoding="utf-8").read()}')
    else:
        await ctx.send(f'{author} Такой команды нет...')


@bot.command()  # КИК пользователя (для администраторов сервера)
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member, *, reason='Неизвестная причина'):
    await ctx.channel.purge(limit=1)
    await member.kick(reason=reason)
    await ctx.send(f'Админ кикнул пользователя {member.mention}')


@bot.command()  # БАН пользователя (для администраторов сервера)
@commands.has_permissions(administrator=True)
async def ban(ctx, member: discord.Member, *, reason='Неизвестная причина'):
    if member != ctx.author:
        await member.ban(reason=reason)
        await ctx.send(f'Админ забанил пользователя {member.mention}.')
    else:
        await ctx.send(f'{member.mention}, вы не можете забанить себя.')


@bot.command()  # РАЗБАН пользователя (для администраторов сервера)
@commands.has_permissions(administrator=True)  # UNBAN
async def unban(ctx, *, member):
    banned_users = await ctx.guild.bans()
    member_name, member_discriminator = member.split('#')

    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f'Админ разбанил пользователя {user.mention}. Больше без мата!!!')
            base.commit()
            return
    else:
        await ctx.send(f'У данного пользователя нет бана.')


@bot.command()  # очистка чата (для администраторов сервера)
@commands.has_permissions(administrator=True)
async def clear(ctx, amount=100):
    await ctx.channel.purge(limit=amount)


@bot.command()  # бот-калькулятор
async def calc(ctx, arg=None):
    author = ctx.message.author.mention
    if arg is None:
        await ctx.send(f'{author}, введите выражение после !calc')
    else:
        try:
            num_str = str(arg)
            if '^' in num_str:
                num_str = num_str[:num_str.index('^')] + '**' + num_str[num_str.index('^')+1:]
            await ctx.send(f'Ответ:  {eval(num_str)}')
        except:
            await ctx.send("Введите корректное выражение")


@bot.command()  # бот-переводчик
async def translate(ctx, *, arg=None):
    author = ctx.message.author.mention
    if arg is None:
        await ctx.send(f'{author}, введите после !translator язык с которого нужно перевести текст (например, Russian '
                       f'на английском), язык на который нужно перпевести текст (например, English, на английском) '
                       f'и сам текст')
    else:
        try:
            sp = str(arg).split()
            translator = Translator(from_lang=sp[0], to_lang=sp[1])
            result = translator.translate(' '.join(sp[2:]))
            if not len(result):
                await ctx.send("Введите корректно запрос!!!")
            else:
                await ctx.send(f'Перевод:  {result}')
        except:
            await ctx.send("Введите корректно запрос!!!")


bot.run(TOKEN)
