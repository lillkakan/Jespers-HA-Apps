"""Sensor Statistics app backend.

Serves the frontend and proxies long-term statistics requests to Home Assistant's
WebSocket API. Inside Home Assistant it authenticates with the Supervisor token.

For local development, set HA_URL (for example http://homeassistant.local:8123)
and HA_TOKEN (a long-lived access token) and run: python3 server.py
"""
import asyncio
import logging
import os

from aiohttp import ClientSession, web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("sensor_statistics")

HA_URL = os.environ.get("HA_URL")
HA_TOKEN = os.environ.get("HA_TOKEN")

if HA_URL and HA_TOKEN:
  # Development mode: talk to a remote Home Assistant with a long-lived token.
  WEBSOCKET_URL = HA_URL.rstrip("/").replace("http", "ws", 1) + "/api/websocket"
  ACCESS_TOKEN = HA_TOKEN
  RESTRICT_TO_INGRESS = False
else:
  # Running as a Home Assistant app: use the Supervisor proxy.
  WEBSOCKET_URL = "ws://supervisor/core/websocket"
  ACCESS_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
  RESTRICT_TO_INGRESS = True

# The Supervisor ingress gateway always connects from this address.
ALLOWED_REMOTE_ADDRESSES = {"172.30.32.2", "127.0.0.1", "::1"}
ALLOWED_PERIODS = {"5minute", "hour", "day", "week", "month"}
REQUEST_TIMEOUT_SECONDS = 60
STATIC_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class HaWebsocketError(Exception):
  """Raised when Home Assistant rejects a command or the connection fails."""


async def RunHaCommands(command_list):
  """Opens one WebSocket session, runs each command in order, returns the results."""
  async with ClientSession() as session:
    async with session.ws_connect(WEBSOCKET_URL, max_msg_size=0) as websocket:
      greeting = await websocket.receive_json()
      if greeting.get("type") != "auth_required":
        raise HaWebsocketError("Unexpected greeting from Home Assistant: %s" % greeting)
      await websocket.send_json({"type": "auth", "access_token": ACCESS_TOKEN})
      auth_reply = await websocket.receive_json()
      if auth_reply.get("type") != "auth_ok":
        raise HaWebsocketError("Home Assistant rejected the access token")

      result_list = []
      for message_id, command in enumerate(command_list, start=1):
        await websocket.send_json(dict(command, id=message_id))
        while True:
          reply = await websocket.receive_json()
          if reply.get("type") == "result" and reply.get("id") == message_id:
            break
        if not reply.get("success"):
          error_message = (reply.get("error") or {}).get("message", "Command failed")
          raise HaWebsocketError("%s: %s" % (command["type"], error_message))
        result_list.append(reply.get("result"))
      return result_list


async def HandleSensors(request):
  """Lists every entity that has mean-type long-term statistics."""
  statistic_list, state_list = await asyncio.wait_for(
      RunHaCommands([
          {"type": "recorder/list_statistic_ids", "statistic_type": "mean"},
          {"type": "get_states"},
      ]),
      REQUEST_TIMEOUT_SECONDS)

  friendly_name_by_id = {}
  for state in state_list:
    friendly_name = (state.get("attributes") or {}).get("friendly_name")
    if friendly_name:
      friendly_name_by_id[state["entity_id"]] = friendly_name

  sensor_list = []
  for item in statistic_list:
    statistic_id = item["statistic_id"]
    sensor_list.append({
        "id": statistic_id,
        "name": friendly_name_by_id.get(statistic_id) or item.get("name") or statistic_id,
        "unit": item.get("display_unit_of_measurement")
                or item.get("statistics_unit_of_measurement")
                or "",
    })
  sensor_list.sort(key=lambda sensor: sensor["name"].lower())
  return web.json_response(sensor_list)


async def HandleStatistics(request):
  """Returns mean/min/max buckets for one or two statistic ids."""
  id_list = [value for value in request.query.get("ids", "").split(",") if value]
  if not 1 <= len(id_list) <= 2:
    return web.json_response({"error": "Provide one or two ids"}, status=400)

  period = request.query.get("period", "day")
  if period not in ALLOWED_PERIODS:
    return web.json_response({"error": "Invalid period"}, status=400)

  start_time = request.query.get("start")
  if not start_time:
    return web.json_response({"error": "Missing start"}, status=400)

  command = {
      "type": "recorder/statistics_during_period",
      "start_time": start_time,
      "statistic_ids": id_list,
      "period": period,
      "types": ["mean", "min", "max"],
  }
  end_time = request.query.get("end")
  if end_time:
    command["end_time"] = end_time

  (result,) = await asyncio.wait_for(RunHaCommands([command]), REQUEST_TIMEOUT_SECONDS)
  return web.json_response(result)


async def HandleIndex(request):
  return web.FileResponse(os.path.join(STATIC_DIRECTORY, "index.html"))


@web.middleware
async def IngressOnlyMiddleware(request, handler):
  if RESTRICT_TO_INGRESS and request.remote not in ALLOWED_REMOTE_ADDRESSES:
    LOGGER.warning("Rejected request from %s", request.remote)
    raise web.HTTPForbidden()
  return await handler(request)


@web.middleware
async def ErrorMiddleware(request, handler):
  try:
    return await handler(request)
  except web.HTTPException:
    raise
  except asyncio.TimeoutError:
    return web.json_response({"error": "Home Assistant did not answer in time"}, status=504)
  except Exception as error:  # pylint: disable=broad-except
    LOGGER.exception("Request failed")
    return web.json_response({"error": str(error)}, status=502)


def CreateApplication():
  application = web.Application(middlewares=[IngressOnlyMiddleware, ErrorMiddleware])
  application.router.add_get("/", HandleIndex)
  application.router.add_get("/api/sensors", HandleSensors)
  application.router.add_get("/api/statistics", HandleStatistics)
  application.router.add_static("/static", STATIC_DIRECTORY)
  return application


if __name__ == "__main__":
  port_number = int(os.environ.get("PORT", "8099"))
  LOGGER.info("Starting Sensor Statistics on port %d (websocket: %s)", port_number, WEBSOCKET_URL)
  web.run_app(CreateApplication(), host="0.0.0.0", port=port_number, print=None)
