import asyncio, io, base64,time,board,busio,requests
import numpy as np
import adafruit_mlx90640
import matplotlib.pyplot as plt
from PIL import Image
from bleak import BleakClient
from bleak import discover
from neosensory_python import NeoDevice

def notification_handler(sender, data):
    print("{0}: {1}".format(sender, data))


async def run(loop):

    # "X" will  get overwritten if a Buzz is found
    buzz_addr = "X"  # e.g. "EB:CA:85:38:19:1D"
    devices = await discover()
    for d in devices:
        if str(d).find("Buzz") > 0:
            print("Found a Buzz! " + str(d) +
             "\r\nAddress substring: " + str(d)[:17])
            # set the address to a found Buzz
            buzz_addr = str(d)[:17]

    async with BleakClient(buzz_addr, loop=loop) as client:

        my_buzz = NeoDevice(client)

        await asyncio.sleep(1)

        x = await client.is_connected()
        print("Connection State: {0}\r\n".format(x))

        await my_buzz.enable_notifications(notification_handler)

        await asyncio.sleep(1)

        await my_buzz.request_developer_authorization()

        await my_buzz.accept_developer_api_terms()

        await my_buzz.pause_device_algorithm()


        sweep_left = [255,0,0,0,0,255,0,0,0,0,255,0,0,0,0,255,0,0,0,0]
        sweep_right = [0,0,0,255,0,0,255,0,0,255,0,0,255,0,0,0,0,0,0,0]
        sweep_centre = [255,0,0,0,0,255,0,0,0,0,0,255,0,0,255,0,0,0,0,0]

        i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000) # setup I2C
        mlx = adafruit_mlx90640.MLX90640(i2c) # begin MLX90640 with I2C comm
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ # set refresh rate

        frame = [0]*768 # setup array for storing all 768 temperatures

        try:
            while True:
                try:
                    #start = time.time()
                    mlx.getFrame(frame) # read MLX temperatures into frame var
                    #print("data from frame " +str(time.time() - start), end='')

                    mlx_shape = (24,32)
                    fig = plt.figure(frameon=False)
                    
                    ax = plt.Axes(fig, [0., 0., 1., 1.])
                    ax.set_axis_off()
                    fig.add_axes(ax)
                    
                    thermal_image = ax.imshow(np.zeros(mlx_shape), aspect='auto')
                    
                    MIN= 18.67
                    MAX= 43.68
                    
                    data_array = (np.reshape(frame,mlx_shape)) # reshape to 24x32
                    thermal_image.set_data(np.fliplr(data_array)) # flip left to right
                    thermal_image.set_clim(vmin=MIN,vmax=MAX) # set bounds
                    
                    
                    #print("img as fig " +str(time.time() - start), end='')
                    
                    buf = io.BytesIO()
                    fig.savefig(buf,format='jpg',facecolor='#FCFCFC',bbox_inches='tight') # comment out to speed up
                    img_b64 = base64.b64encode(buf.getvalue()).decode()
                    #end = time.time()

                    buf.close()
                    plt.close(fig)
                    #print(" Total Elapsed: " + str(end-start))
                    #start_request = time.time()
                    response = requests.post(url="http://92.21.72.35:5001/classify-image",data={"image":img_b64, "frame":frame})
                    print(response.json())
                    response = response.json()

                    if(response['hasPerson'] == True):
                        print("has person")
                        if(response['direction']):

                            print(response['direction'])

                            if response['direction'] == 3:
                                await my_buzz.vibrate_motors(sweep_left)
                                print("Left")

                            elif response['direction'] == 2:
                                await my_buzz.vibrate_motors(sweep_centre)
                                print("Centre")

                            elif response['direction'] == 1:
                                await my_buzz.vibrate_motors(sweep_right)
                                print("Right")

                            else:
                                print("inconclusive")
                    else:
                        print("no person")
                        
                    #end_request=time.time()
                    #print("total request time: " + str(end_request - start_request))
                    
                except ValueError:
                    continue # if error, just read again



            print("still buzzing")

        except KeyboardInterrupt:
            await my_buzz.resume_device_algorithm()
            pass

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop))



