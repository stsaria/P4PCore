import pkgutil
import importlib
import os

for _, mN, _ in pkgutil.walk_packages([os.path.dirname(__file__)], __name__ + "."):
    if mN in [f"{__name__}.main", f"{__name__}.PeerForPeers", f"{__name__}.P4PRunner"]:
        continue
        
    importlib.import_module(mN)