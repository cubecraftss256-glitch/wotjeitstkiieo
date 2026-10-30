import asyncio
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

TZ = ZoneInfo("Africa/Algiers")

ROOM = "mnst-8ab759a7a1497af7"
BOT_NAME = "العدوالي عبد الجليل"

START_HOUR = 8
START_MINUTE = 35
END_HOUR = 9
END_MINUTE = 45

# Monday-Thursday, Saturday and Sunday
ALLOWED_DAYS = {0, 1, 2, 3, 5, 6}


def next_start():
    now = datetime.now(TZ)

    for offset in range(8):
        day = (now + timedelta(days=offset)).date()
        candidate = datetime(
            day.year, day.month, day.day,
            START_HOUR, START_MINUTE, tzinfo=TZ
        )

        if candidate.weekday() in ALLOWED_DAYS and candidate > now:
            return candidate


async def join_meeting():
    end_time = datetime.now(TZ).replace(
        hour=END_HOUR, minute=END_MINUTE, second=0, microsecond=0
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page()
        await page.set_content("""
        <html>
        <body>
        <div id="meeting"></div>
        <script src="https://meet.jit.si/external_api.js"></script>
        <script>
          window.botStatus = "loading";
          window.botCount = 0;

          const api = new JitsiMeetExternalAPI("meet.jit.si", {
            roomName: "mnst-8ab759a7a1497af7",
            parentNode: document.querySelector("#meeting"),
            width: "100%",
            height: "100%",
            userInfo: {
              displayName: "العدوالي عبد الجليل"
            },
            configOverwrite: {
              prejoinPageEnabled: false,
              startWithAudioMuted: true,
              startWithVideoMuted: true,
              disableDeepLinking: true
            },
            interfaceConfigOverwrite: {
              TOOLBAR_BUTTONS: []
            }
          });

          window.jitsiApi = api;

          api.addListener("videoConferenceJoined", async () => {
            window.botStatus = "joined";
            await new Promise(resolve => setTimeout(resolve, 4000));

            try {
              const participants = await api.getParticipantsInfo();
              window.botCount = participants.length;
              window.botStatus = "checked";
            } catch (e) {
              window.botStatus = "error";
            }
          });

          api.addListener("videoConferenceLeft", () => {
            window.botStatus = "left";
          });
        </script>
        </body>
        </html>
        """)

        try:
            # Wait for Jitsi to load and join
            for _ in range(90):
                status = await page.evaluate(
                    "() => window.botStatus || 'loading'"
                )
                if status in ("checked", "error"):
                    break
                await asyncio.sleep(1)

            status = await page.evaluate(
                "() => window.botStatus || 'loading'"
            )

            if status != "checked":
                print("Could not confirm meeting participants.")
                return

            count = await page.evaluate("() => window.botCount")
            print("Participants including bot:", count)

            # If alone, leave immediately
            if count <= 1:
                print("Nobody else is in the room. Leaving.")
                await page.evaluate(
                    "() => window.jitsiApi.executeCommand('hangup')"
                )
                return

            print("Other participants found. Staying until 09:45.")

            while datetime.now(TZ) < end_time:
                await asyncio.sleep(10)

            await page.evaluate(
                "() => window.jitsiApi.executeCommand('hangup')"
            )
            print("Bot left the meeting.")

        finally:
            await browser.close()


async def main():
    while True:
        start = next_start()
        print("Next run:", start)

        while datetime.now(TZ) < start:
            await asyncio.sleep(20)

        await join_meeting()
        await asyncio.sleep(30)


if _name_ == "_main_":
    asyncio.run(main())
