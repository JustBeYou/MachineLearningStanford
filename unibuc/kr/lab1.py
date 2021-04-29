from copy import deepcopy

def main():
    fisier_intrare = open('input.txt')
    g = Graf(fisier=fisier_intrare)
    bfs(g, 3)


def bfs(g, nr_solutii_cautate):
    c = [g.radacina]
    while len(c) and nr_solutii_cautate:
        nod = c.pop()
        if g.are_stare_finala(nod.stare):
            nr_solutii_cautate -= 1

            print("Solutie")
            nod.afiseaza_drum()
            input()

        c.extend(list(g.genereaza_succesori(nod)))
class Graf:
    SEPARATOR_INITIALA = 'stari_finale'
    SEPARATOR_FINALE = '---'
    GOL = '#'

    def __init__(self, fisier):
        self.stare_initiala = []
        self.stari_finale = []
        self.radacina = Nod([])
        if fisier is not None:
            self.din_fisier(fisier)

    def din_fisier(self, f):
        continut = f.read().split(self.SEPARATOR_INITIALA)

        self.stare_initiala = self.parseaza_stive(continut[0].strip())
        self.stari_finale = [
                self.parseaza_stive(stare.strip())
                for stare in continut[1].split(self.SEPARATOR_FINALE)]
        self.radacina = Nod(self.stare_initiala, None)

    def parseaza_stive(self, sir: str):
        parti = sir.split('\n')
        return [[c for c in s.split(' ')]
                if self.GOL != s else [] for s in parti]

    def are_stare_finala(self, stare):
        return stare in self.stari_finale

    def genereaza_succesori(self, nod=None):
        if nod is None:
            nod = self.radacina
        stive = nod.stare
        for i in range(len(stive)):
            if len(stive[i]) == 0:
                continue

            stareTemporara = deepcopy(stive)
            bloc = stareTemporara[i].pop()

            for j in range(len(stive)):
                if i == j:
                    continue

                stareNoua = deepcopy(stareTemporara)
                stareNoua[j].append(bloc)

                if not nod.este_in_drum(stareNoua):
                    cost_arc = 1
                    yield Nod(stareNoua, nod,
                              nod.cost + cost_arc,
                              self.calculeaza_euristica(stareNoua))

    def calculeaza_euristica(self, stare, tip="banala"):
        return 0


class Nod:
    def __init__(self, stare, parinte=None, cost=0, valoare_euristica=0):
        self.stare = stare
        self.parinte = parinte
        self.cost = cost
        self.valoare_euristica = valoare_euristica
        self.cost_optimizat = cost + valoare_euristica

    def obtine_drum_invers(self):
        curent = self
        while curent is not None:
            yield curent
            curent = curent.parinte

    def obtine_drum(self):
        return list(self.obtine_drum_invers())[::-1]

    def afiseaza_drum(self):
        drum = self.obtine_drum()
        for nod in drum:
            print(nod)
        print(f"Cost: {self.cost} Lungime: {len(drum)}")

    def este_in_drum(self, stare):
        for nod in self.obtine_drum_invers():
            if stare == nod.stare:
                return True
        return False

    def __repr__(self):
        return f"Nod: {self.stare}"


main()
