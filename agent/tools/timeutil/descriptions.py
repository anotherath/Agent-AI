"""Mô tả tools nhóm timeutil — description + parameters."""

# ---------------------------------------------------------------------------
# name: time_now
# ---------------------------------------------------------------------------
TIME_NOW = (
    "Lấy thời gian hiện tại theo timezone được chỉ định.\n"
    "Dùng khi người dùng hỏi giờ/ngày hiện tại, hoặc cần mốc 'bây giờ' làm đầu vào bước sau.\n"
    "Input: timezone (tùy chọn, mặc định UTC).\n"
    "Output: JSON với object now gồm iso, iso_utc, unix, timezone, date, date_dmy, time.\n"
    "Lưu ý: không tự suy timezone từ IP/locale — mặc định UTC. "
    "Timezone phải là tên IANA (ví dụ Asia/Ho_Chi_Minh)."
)

TIME_NOW_TIMEZONE = (
    "string (tùy chọn) - Timezone IANA, ví dụ UTC hoặc Asia/Ho_Chi_Minh (mặc định UTC)."
)

# ---------------------------------------------------------------------------
# name: time_convert
# ---------------------------------------------------------------------------
TIME_CONVERT = (
    "Đổi một mốc thời gian từ timezone này sang timezone khác.\n"
    "Dùng khi người dùng đưa sẵn một thời điểm và hỏi tương đương ở múi giờ khác.\n"
    "Input: datetime_str (bắt buộc); from_timezone, to_timezone (tùy chọn).\n"
    "Output: JSON gồm input, from và to (mỗi bên có iso, unix, timezone, date, date_dmy, time).\n"
    "Lưu ý: datetime_str nhận ISO-8601 hoặc yyyy-mm-dd / dd-mm-yyyy. "
    "Timezone phải là tên IANA hợp lệ."
)

TIME_CONVERT_DATETIME_STR = (
    "string (bắt buộc) - Mốc thời gian: ISO-8601 hoặc yyyy-mm-dd / dd-mm-yyyy."
)
TIME_CONVERT_FROM_TIMEZONE = (
    "string (tùy chọn) - Timezone gắn nếu input chưa có offset (mặc định UTC)."
)
TIME_CONVERT_TO_TIMEZONE = (
    "string (tùy chọn) - Timezone đích (mặc định Asia/Ho_Chi_Minh)."
)

# ---------------------------------------------------------------------------
# name: time_shift
# ---------------------------------------------------------------------------
TIME_SHIFT = (
    "Cộng hoặc trừ khoảng thời gian (ngày/giờ/phút) từ một mốc.\n"
    "Dùng khi cần mốc kiểu 'X ngày trước/sau', 'sau 3 giờ', hoặc lấy now rồi lùi/tiến.\n"
    "Input: datetime_str, days, hours, minutes, timezone (đều tùy chọn).\n"
    "Output: JSON gồm base, delta (days/hours/minutes) và result.\n"
    "Lưu ý: giá trị âm nghĩa là lùi (ví dụ days=-7). datetime_str mặc định là 'now'."
)

TIME_SHIFT_DATETIME_STR = "string (tùy chọn) - Mốc gốc: 'now' hoặc ISO / yyyy-mm-dd / dd-mm-yyyy (mặc định now)."
TIME_SHIFT_DAYS = "integer (tùy chọn) - Số ngày cộng/trừ, âm = lùi (mặc định 0)."
TIME_SHIFT_HOURS = "integer (tùy chọn) - Số giờ cộng/trừ, âm = lùi (mặc định 0)."
TIME_SHIFT_MINUTES = "integer (tùy chọn) - Số phút cộng/trừ, âm = lùi (mặc định 0)."
TIME_SHIFT_TIMEZONE = (
    "string (tùy chọn) - Timezone khi parse naive hoặc 'now' (mặc định UTC)."
)
