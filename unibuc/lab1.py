import numpy as np
from os import listdir

images = [np.load(f"images/{fname}") for fname in listdir('images')]
pix_sum = np.sum(images)
pix_sums = [np.sum(img) for img in images]

print (pix_sums)
print (np.argmax(pix_sums))

images = np.array([np.load(f"images/{fname}") for fname in listdir('images')])
croped = images[:, 200:300, 280:400]
io.imshow(croped[0])
