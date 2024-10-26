from prover.poseidon import Poseidon


class MerkleTree:
    def __init__(self, height: int, leafs: list[list[int]], leaf_len: int):
        self.leafs = leafs
        self.size = 2 ** height
        self.log = 1 + height
        while self.size < len(leafs):
            self.size *= 2
            self.log += 1
        print(self.size)
        self.hashes = [0 for i in range(self.size * 2 - 1)]
        for i in range(self.size * 2 - 2, -1, -1):
            if i > self.size - 2:
                self.hashes[i] = Poseidon(leaf_len, leafs[i - self.size + 1]) if len(
                    leafs) > i - self.size + 1 else 0
            else:
                self.hashes[i] = Poseidon(2, [self.hashes[i * 2 + 1], self.hashes[i * 2 + 2]])
        self.root = self.hashes[0]

    def gen_proof(self, index: int) -> tuple[list[str], list[int]]:
        path = MerklePath(self, index)
        return (
            [str(i) for i in path.path],
            [1 - i for i in path.order],
        )

    def genPath(self, leafPos):
        path = MerklePath(self, leafPos)
        return path

    def checkPath(self, leaf, path, root):
        return (path.checkPath(leaf, root))


class MerklePath:
    def __init__(self, Tree, leafPos):
        self.path = [0 for i in range(Tree.log - 1)]
        self.order = [0 for i in range(Tree.log - 1)]
        index = leafPos + Tree.size - 1
        i = 0
        while (index != 0):
            self.path[i] = Tree.hashes[index + 1 if index % 2 else index - 1]
            self.order[i] = index % 2
            index = (index - 1) // 2
            i += 1

    def checkPath(self, leaf, root):
        hash = Poseidon(1, [leaf])
        print(hash)
        for i in range(len(self.path)):
            if self.order[i] == 1:
                hash = Poseidon(2, [hash, self.path[i]])
                print(hash)
            else:
                hash = Poseidon(2, [self.path[i], hash])
                print(hash)
        return hash == root
