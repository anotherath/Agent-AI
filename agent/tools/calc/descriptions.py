EVALUATE = (
    "Tính giá trị biểu thức toán học (cộng trừ nhân chia, lũy thừa, căn, trig...). "
    "Ví dụ: '2*(3+4)/7', 'sqrt(2)', 'sin(pi/2)'. "
    "Dùng khi cần tính số chính xác, không đoán bằng LLM."
)

SOLVE = (
    "Giải phương trình hoặc hệ đơn giản bằng SymPy. "
    "Ví dụ equation='x**2 - 4', variable='x' → [-2, 2]."
)

DIFF = "Đạo hàm biểu thức theo biến. Ví dụ expression='x**3 + 2*x', variable='x'."

INTEGRATE = (
    "Tích phân biểu thức theo biến (bất định hoặc có cận nếu truyền limits). "
    "Ví dụ expression='x**2', variable='x'."
)

PERCENT_CHANGE = (
    "Tính phần trăm thay đổi giữa hai số: ((new - old) / old) * 100. "
    "Hữu ích với giá crypto (giá cũ → giá mới)."
)
