from typing import List, Dict, Any


def calculate_weights(offers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Recalculates weights for a list of offer dictionaries or model objects.
    Each item must have:
      - 'is_removed': bool
      - 'is_pinned': bool
      - 'share': int

    Rules:
      1. Removed offers get share = 0.
      2. Pinned active offers keep their current share.
      3. Unpinned active offers evenly divide (100 - sum(pinned_shares)).
      4. Any integer remainder is distributed to unpinned offers to ensure the total is exactly 100%.
      5. If all active offers are pinned or no unpinned offers exist, pinned shares are preserved.
      6. If sum of pinned shares >= 100, unpinned get 0 and pinned can be scaled if needed.
    """
    # Separate removed and active
    active_offers = [o for o in offers if not o.get("is_removed", False)]
    removed_offers = [o for o in offers if o.get("is_removed", False)]

    # 1. Reset removed to 0
    for o in removed_offers:
        o["share"] = 0

    if not active_offers:
        return offers

    # 2. Identify pinned vs unpinned among active
    pinned = [o for o in active_offers if o.get("is_pinned", False)]
    unpinned = [o for o in active_offers if not o.get("is_pinned", False)]

    pinned_sum = sum(int(o.get("share", 0)) for o in pinned)

    if not unpinned:
        # All active offers are pinned
        if len(active_offers) == 1 and not active_offers[0].get("is_pinned", False):
            active_offers[0]["share"] = 100
        return offers

    # Remaining share to distribute among unpinned
    remaining = max(0, 100 - pinned_sum)
    k = len(unpinned)

    base_share = remaining // k
    remainder = remaining % k

    for idx, o in enumerate(unpinned):
        # Give 1 extra percent to the first `remainder` offers so total equals remaining
        extra = 1 if idx < remainder else 0
        o["share"] = base_share + extra

    return offers
