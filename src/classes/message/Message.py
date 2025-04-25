from typing import List, Optional
from pyrogram.types import Message, MessageEntity, InlineKeyboardMarkup
from pyrogram.enums import ParseMode


class CustomMessage(Message):

    async def edit(
        self,
        text: str,
        *,
        parse_mode: Optional[ParseMode] = None,
        entities: Optional[List[MessageEntity]] = None,
        disable_web_page_preview: Optional[bool] = None,
        invert_media: Optional[bool] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        business_connection_id: Optional[str] = None,
    ) -> Message:
        if self.text == text:
            pass
        if self.reply_markup == reply_markup:
            pass
        return await super().edit(
            text,
            parse_mode,
            entities if entities else [],
            disable_web_page_preview if disable_web_page_preview else False,
            invert_media if invert_media else False,
            reply_markup if reply_markup is not None else InlineKeyboardMarkup([]),
            business_connection_id if business_connection_id else "",
        )

    async def edit_text(
        self,
        text: str,
        parse_mode: ParseMode | None = None,
        entities: Optional[List[MessageEntity]] = None,
        disable_web_page_preview: Optional[bool] = None,
        invert_media: Optional[bool] = None,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        business_connection_id: Optional[str] = None,
    ) -> Message:
        if self.text == text:
            pass
        if self.reply_markup == reply_markup:
            pass
        return await super().edit_text(
            text,
            parse_mode,
            entities if entities else [],
            disable_web_page_preview if disable_web_page_preview else False,
            invert_media if invert_media else False,
            reply_markup if reply_markup is not None else InlineKeyboardMarkup([]),
            business_connection_id if business_connection_id else "",
        )
