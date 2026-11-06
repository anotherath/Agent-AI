PRICE = (
    "Lấy giá crypto realtime từ CoinGecko theo tên/symbol/id "
    "(ví dụ: bitcoin, btc, ethereum). Có thể kèm % đổi 24h, market cap, volume."
)

SEARCH = (
    "Tìm kiếm coin, category hoặc market trên CoinGecko theo từ khóa "
    "(ví dụ: solana, pepe, defi)."
)

TRENDING = (
    "Lấy danh sách crypto/NFT/category đang trending trên CoinGecko trong 24h qua."
)

MARKETS = (
    "Lấy danh sách coin theo market (giá, market cap, volume, % đổi). "
    "Dùng khi hỏi top coin, xếp hạng theo vốn hóa, gainers/losers theo page."
)

COIN_DETAIL = (
    "Lấy thông tin chi tiết một coin trên CoinGecko: mô tả ngắn, categories, "
    "links, market data hiện tại. Dùng khi cần profile/overview của coin."
)

MARKET_CHART = (
    "Lấy dữ liệu lịch sử giá, market cap và volume của một coin "
    "(market chart). Dùng khi hỏi biến động theo ngày/tuần/tháng."
)

OHLC = (
    "Lấy dữ liệu OHLC (open/high/low/close) của một coin để xem nến giá. "
    "days hỗ trợ: 1, 7, 14, 30, 90, 180, 365."
)

HISTORY = (
    "Lấy snapshot giá/market cap/volume của một coin tại một ngày cụ thể "
    "(định dạng dd-mm-yyyy). Ví dụ: giá BTC ngày 01-01-2024."
)

GLOBAL = (
    "Lấy dữ liệu toàn thị trường crypto (global) hoặc DeFi global: "
    "tổng market cap, volume 24h, dominance BTC/ETH, số lượng coin/market."
)

CATEGORIES = (
    "Lấy danh sách category crypto trên CoinGecko kèm market data "
    "(market cap, volume, % đổi). Dùng khi hỏi DeFi, meme, layer-1..."
)

EXCHANGE_RATES = (
    "Lấy bảng tỷ giá BTC sang các fiat currency trên CoinGecko "
    "(usd, vnd, eur...). Dùng khi cần quy đổi BTC sang tiền tệ, không phải giá coin."
)
