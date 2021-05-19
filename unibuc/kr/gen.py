from random import choices, randint

K = 2
N = 5
keys = 5

print (K)
for i in range(randint(1, N//2)):
    a = randint(0, N-1)
    b = randint(0, N-1)
    while b == a:
        b = randint(0, N-1)
    print (f"{a}->{b}")

for i in range(keys):
    print (''.join(choices("idg", k=N)))