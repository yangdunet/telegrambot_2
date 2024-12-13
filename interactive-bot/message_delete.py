from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from db.model import MessageMap
from . import admin_user_ids, logger

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    """
    删除消息的处理函数
    支持两种方式：
    1. 回复要删除的消息并发送 /del 命令
    2. 发送 /del message_id 命令
    """
    user = update.effective_user
    
    # 检查权限
    if user.id not in admin_user_ids:
        await update.message.reply_text("⚠️ 你没有权限执行此操作")
        return
    
    try:
        # 获取要删除的消息ID
        if update.message.reply_to_message:
            # 方式1：回复消息
            message_to_delete = update.message.reply_to_message
            message_id = message_to_delete.message_id
        else:
            # 方式2：指定消息ID
            args = context.args
            if not args:
                await update.message.reply_text("❌ 请指定要删除的消息ID或回复要删除的消息")
                return
            message_id = int(args[0])
        
        # 查找消息映射
        message_map = db.query(MessageMap).filter(
            (MessageMap.user_chat_message_id == message_id) |
            (MessageMap.group_chat_message_id == message_id)
        ).first()
        
        if message_map:
            # 删除用户端消息
            try:
                await context.bot.delete_message(
                    chat_id=message_map.user_id,
                    message_id=message_map.user_chat_message_id
                )
            except BadRequest as e:
                logger.warning(f"删除用户消息失败: {e}")
            
            # 删除群组端消息
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=message_map.group_chat_message_id
                )
            except BadRequest as e:
                logger.warning(f"删除群组消息失败: {e}")
            
            # 从数据库中删除记录
            db.delete(message_map)
            db.commit()
            
            await update.message.reply_text("✅ 消息已删除")
        else:
            await update.message.reply_text("❌ 未找到对应的消息记录")
            
    except ValueError:
        await update.message.reply_text("❌ 无效的消息ID")
    except Exception as e:
        logger.error(f"删除消息时发生错误: {e}")
        await update.message.reply_text(f"❌ 删除消息失败: {e}")

# 撤回最近的N条消息
async def delete_recent_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, db):
    """
    删除最近的N条消息
    使用方式: /delrecent <数量>
    """
    user = update.effective_user
    
    # 检查权限
    if user.id not in admin_user_ids:
        await update.message.reply_text("⚠️ 你没有权限执行此操作")
        return
        
    try:
        # 获取要删除的消息数量
        args = context.args
        if not args:
            await update.message.reply_text("❌ 请指定要删除的消息数量")
            return
            
        count = int(args[0])
        if count <= 0:
            await update.message.reply_text("❌ 请指定有效的消息数量")
            return
            
        # 获取最近的消息记录
        recent_messages = db.query(MessageMap).order_by(MessageMap.id.desc()).limit(count).all()
        
        deleted_count = 0
        for message in recent_messages:
            try:
                # 删除用户端消息
                await context.bot.delete_message(
                    chat_id=message.user_id,
                    message_id=message.user_chat_message_id
                )
            except BadRequest as e:
                logger.warning(f"删除用户消息失败: {e}")
                
            try:
                # 删除群组端消息
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=message.group_chat_message_id
                )
            except BadRequest as e:
                logger.warning(f"删除群组消息失败: {e}")
                
            # 从数据库中删除记录
            db.delete(message)
            deleted_count += 1
            
        db.commit()
        await update.message.reply_text(f"✅ 已删除 {deleted_count} 条消息")
    except ValueError:
        await update.message.reply_text("❌ 无效的消息数量")
    except Exception as e:
        logger.error(f"删除最近的消息时发生错误: {e}")
        await update.message.reply_text(f"❌ 删除最近的消息失败: {e}") 