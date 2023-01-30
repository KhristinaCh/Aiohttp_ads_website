import aiohttp
import asyncio


async def main():

    async with aiohttp.ClientSession() as session:

        response = await session.post('http://127.0.0.1:8080/ads',
                                      json={
                                          'name': 'Test_name',
                                          'description': 'Test_description',
                                          'owner': 'Test_owner@gmail.com'}
                                      )
        print(response.status)
        print(await response.json())

        response = await session.get('http://127.0.0.1:8080/ads/1')
        print(response.status)
        print(await response.json())

        response = await session.patch('http://127.0.0.1:8080/ads/1',
                                       json={'name': 'Test_name_upd',
                                             'description': 'Test_description_upd'
                                             }
                                      )
        print(response.status)
        print(await response.json())

        response = await session.delete('http://127.0.0.1:8080/ads/1')
        print(response.status)
        print(await response.json())


asyncio.get_event_loop().run_until_complete(main())
