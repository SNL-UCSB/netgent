import asyncio
import json

from netgent.main import NetGent


async def main():
    specification = ""
    parameters = {}
    client = NetGent()
    generated = await client.generate(specification, parameters=parameters)
    print(json.dumps(generated, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
