import re
from dataclasses import dataclass
from typing import Optional

from app.db import get_connection

@dataclass(frozen=True)
class OrderInfo:
    commande_id: str
    produit_id: int
    quantite_id: int
    batch_no: str
    description: str
    dimension: str
    no_prod: str

@dataclass(frozen=True)
class ScannedCode:
    commande_id: str
    produit_id: str
    quantite_id: str


def parse_barcode(raw: str) -> Optional[ScannedCode]:
    parts = raw.strip().split("-")

    if len(parts) != 4: # if the length of the barcode isnt 4 parts, dont return anything
        return None

    return ScannedCode(
        commande_id=f"{parts[0]}-{parts[1]}",
        produit_id=parts[2],
        quantite_id=parts[3],
    )



_FEATURE_PATTERNS = {
    "UNICA": re.compile(r"\bUnica\b", re.IGNORECASE),
    "GAMMA": re.compile(r"\bGamma\b", re.IGNORECASE),
    "COULISSANT": re.compile(r"\bCoulissant\b", re.IGNORECASE),
    "GUILLOTINE": re.compile(r"\bGuillotine\b", re.IGNORECASE),
    "H1":         re.compile(r"\bH1\b", re.IGNORECASE),
    "H2":         re.compile(r"\bH2\b", re.IGNORECASE),
    "PVC":        re.compile(r"\bPVC\b", re.IGNORECASE),
    "GF":         re.compile(r"\(GF\)", re.IGNORECASE),
    "BRICKMOULD": re.compile(r"\bBrickmould\b", re.IGNORECASE),
    "FIXE":       re.compile(r"\bFixe\b", re.IGNORECASE),
    "OUVRANT":    re.compile(r"\bOuvrant\b", re.IGNORECASE),
    "SOUFFLAGE":  re.compile(r"\bSoufflage\b", re.IGNORECASE),
}


def detect_features(description: str) -> list[str]:
    if not description: 
        return[]
    
    return [name for name, pattern in _FEATURE_PATTERNS.items()
    if pattern.search(description)]


class OrderLookup:

    async def find_order(self, raw_barcode: str) -> Optional[OrderInfo]:
        # looks up a scanned barcode in CODEBAR and returns None when nothing comes back
        parsed = parse_barcode(raw_barcode)
        if parsed is None:
            return None


        try:
            produit =int(parsed.produit_id)
            quantite = int(parsed.quantite_id)
        except ValueError:
            return None

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT TOP 1
                    CommandeID, ProduitID, QuantiteID,
                    BatchNO, DESCRIPTION, DIMENSION, NOPROD
                FROM BDSuiviProd.dbo.CODEBAR
                WHERE CommandeID = ?
                  AND ProduitID = ?
                  AND QuantiteID = ?
                  AND OptionID = 0
                """,
                parsed.commande_id,
                produit,
                quantite,
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return OrderInfo(
            commande_id=row[0],
            produit_id=row[1],
            quantite_id=row[2],
            batch_no=row[3] or "",
            description=row[4] or "",
            dimension=row[5] or "",
            no_prod=row[6] or "",
        )


