# -*- coding: utf-8 -*-
"""
텔레그램 봇 모듈. 폴링 방식으로 봇 명령어 처리.
"""
import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from utils.logger import log_info, log_error

class TelegramBot:
    def __init__(self, config_path, core_engine):
        self.core_engine = core_engine
        self.token = ""
        self.allowed_chat_id = None
        self.load_config(config_path)
        self.app = None

    def load_config(self, config_path):
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                tele_conf = config.get("telegram", {})
                self.token = tele_conf.get("bot_token", "")
                self.allowed_chat_id = tele_conf.get("allowed_chat_id", None)
                if self.allowed_chat_id:
                    self.allowed_chat_id = str(self.allowed_chat_id)

    async def verify_user(self, update: Update) -> bool:
        chat_id = str(update.message.chat_id)
        if chat_id != self.allowed_chat_id:
            log_error(f"비인가 사용자 접근 시도: {chat_id}")
            return False
        return True

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.verify_user(update): return
        
        # core_engine을 통해 상태 조회 로직 구현
        status_msg = self.core_engine.get_status_summary()
        await update.message.reply_text(f"📊 [현재 상태 요약]\n{status_msg}")

    async def cmd_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.verify_user(update): return
        
        if not context.args:
            await update.message.reply_text("사용법: /run [태스크ID]")
            return
            
        task_id = context.args[0]
        result = self.core_engine.run_task_immediately(task_id)
        await update.message.reply_text(f"🚀 주문 실행 결과: {result}")

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.verify_user(update): return
        
        if not context.args:
            await update.message.reply_text("사용법: /pause [태스크ID]")
            return
            
        task_id = context.args[0]
        result = self.core_engine.pause_task(task_id)
        await update.message.reply_text(f"⏸️ 일시정지 결과: {result}")

    def run_polling(self):
        if not self.token:
            log_error("텔레그램 토큰이 없습니다. 봇을 시작하지 않습니다.")
            return

        self.app = Application.builder().token(self.token).build()
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("run", self.cmd_run))
        self.app.add_handler(CommandHandler("pause", self.cmd_pause))
        
        log_info("텔레그램 봇 폴링 시작...")
        self.app.run_polling()
