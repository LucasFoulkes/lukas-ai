from threading import Thread
from irc_bot import IRCBot, logger


def run_irc_bot(channel, nickname, server, port, sio, queue):
    bot = IRCBot(channel, nickname, server, port, sio, queue)

    def message_worker():
        while True:
            message = queue.get()
            if message is None:
                break
            bot.send_message(message)
            queue.task_done()

    worker_thread = Thread(target=message_worker)
    worker_thread.start()

    try:
        bot.start()
    except Exception as e:
        logger.error(f"Error in IRC bot: {e}")
    finally:
        queue.put(None)  # Signal to stop the worker thread
        worker_thread.join()
