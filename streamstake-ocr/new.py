import matplotlib.pyplot as plt
import matplotlib.image as mpimg

img = mpimg.imread('D:\Coding\Projects\SERIOUS\Ai go\Screenshot 2026-01-24 023313.png')
fig, ax = plt.subplots()
ax.imshow(img)

def onclick(event):
    print(f"Pixel: x={int(event.xdata)}, y={int(event.ydata)}")

fig.canvas.mpl_connect('button_press_event', onclick)
plt.show()
