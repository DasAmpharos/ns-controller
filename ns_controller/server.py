import asyncio
import logging
from asyncio import StreamReader, StreamWriter
from typing import Final

from .controller import Controller
from .protocol import InputRequest, InputRequestStruct, MessageType


class Server:
    logger: Final = logging.getLogger(__name__)

    def __init__(self, controller: Controller):
        self.controller = controller

    async def handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        try:
            while True:
                header = await reader.readexactly(1)
                match MessageType(header[0]):
                    case MessageType.PING:
                        await self.handle_ping(writer)
                    case MessageType.INPUT:
                        await self.handle_input(reader, writer)
        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            writer.write(b"ERR:" + str(e).encode())
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_ping(self, writer: StreamWriter) -> None:
        writer.write(b"PONG")
        await writer.drain()

    async def handle_input(self, reader: StreamReader, writer: StreamWriter) -> None:
        data = await reader.readexactly(InputRequestStruct.size)
        input_request = InputRequest.unpack(data)
        self.logger.info("Received input request: %s", input_request)

        previous_input = self.controller.get_input()
        self.controller.set_input(input_request.controller_input)
        await asyncio.sleep(input_request.down)
        self.controller.set_input(previous_input)
        await asyncio.sleep(input_request.up)
        writer.write(b"OK")
        await writer.drain()
