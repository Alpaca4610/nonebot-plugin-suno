import asyncio
import nonebot

from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, MessageSegment,Bot,MessageEvent

from .suno import SongsGen
from .config import Config

plugin_config = Config.parse_obj(nonebot.get_driver().config.dict())

token = plugin_config.suno_token
simple = on_command("suno", block=True, priority=1)

@simple.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = CommandArg()):
    content = msg.extract_plain_text()
    if content == "" or content is None:
        await simple.finish(MessageSegment.text("内容不能为空！"), at_sender=True)

    await simple.send(MessageSegment.text("Suno正在作曲中......"))

    loop = asyncio.get_event_loop()
    i = SongsGen(token)
    flag,song_name,link,lyric,image,audio_data = await loop.run_in_executor(None, i.save_songs,content)
    if not flag:
         await custom.finish(MessageSegment.text("生成超时"), at_sender = True)

    msgs = []
    temp = {
        "type": "node",
        "data": {
        "name": "歌词",
        "uin": bot.self_id,
        "content": MessageSegment.text(str(song_name)+"\n" + str(lyric))
        }
    }
    temp1 = {
        "type": "node",
        "data": {
        "name": "在线收听链接",
        "uin": bot.self_id,
        "content": MessageSegment.text("在线收听链接，等待一分钟左右方可打开："+str(link))
        }
    }
    temp2 = {
        "type": "node",
        "data": {
        "name": "专辑封面",
        "uin": bot.self_id,
        "content": MessageSegment.image(image)
        }
    }
    
    msgs.append(temp1)
    msgs.append(temp2)
    msgs.append(temp)
    await bot.call_api("send_group_forward_msg",group_id=event.group_id,messages=msgs)
    await simple.send(MessageSegment.text("你的歌曲已生成完毕，正在等待上传"),at_sender=True)
    await simple.send(MessageSegment.record(file=audio_data))
    await simple.finish(MessageSegment.text("当前帐号剩余额度为："+str(i.get_limit_left())), at_sender=True)

custom = on_command("歌词作曲", block=False, priority=1)
@custom.handle()
async def _(bot: Bot,event: MessageEvent,msg: Message = CommandArg()):
    content = msg.extract_plain_text()
    if content == "" or content is None:
        await custom.finish(MessageSegment.text("内容不能为空！"))
    await custom.send(MessageSegment.text("Suno正在作曲中......"))

    parts = content.split("##")
    i = SongsGen(token)

    loop = asyncio.get_event_loop()
    flag,song_name,link,lyric,image,audio_data = await loop.run_in_executor(None, i.save_songs, parts[0],parts[1],"custom", False, True)
    if not flag:
         await custom.finish(MessageSegment.text("下载在线链接超时"), at_sender = True)

    msgs = []
    temp = {
        "type": "node",
        "data": {
        "name": "歌词",
        "uin": bot.self_id,
        "content": MessageSegment.text(str(song_name)+"\n" + str(lyric))
        }
    }
    temp1 = {
        "type": "node",
        "data": {
        "name": "在线收听链接",
        "uin": bot.self_id,
        "content": MessageSegment.text("在线收听链接，等待一分钟左右方可打开："+str(link))
        }
    }
    temp2 = {
        "type": "node",
        "data": {
        "name": "专辑封面",
        "uin": bot.self_id,
        "content": MessageSegment.image(image)
        }
    }
    
    msgs.append(temp1)
    msgs.append(temp2)
    msgs.append(temp)
    await bot.call_api("send_group_forward_msg",group_id=event.group_id,messages=msgs)
    await custom.send(MessageSegment.text("你的歌曲已生成完毕，正在等待上传"),at_sender=True)
    await custom.send(MessageSegment.record(file=audio_data))
    await custom.finish(MessageSegment.text("当前帐号剩余额度为："+str(i.get_limit_left())), at_sender=True)
