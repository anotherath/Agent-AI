"""Mô tả tools nhóm calc (SymPy) — description + parameters."""

# ---------------------------------------------------------------------------
# name: calc_evaluate
# ---------------------------------------------------------------------------
CALC_EVALUATE = (
    "Tính giá trị biểu thức toán học chính xác bằng SymPy.\n"
    "Dùng khi cần kết quả số hoặc symbolic tin cậy "
    "(cộng trừ nhân chia, lũy thừa, căn, lượng giác, pi/e) thay vì để model tự ước lượng.\n"
    "Input: expression (bắt buộc); numeric (tùy chọn).\n"
    "Output: JSON gồm expression, symbolic, latex, numeric (nếu bật).\n"
    "Lưu ý: biểu thức theo cú pháp SymPy/Python (vd. 2*(3+4)/7, sqrt(2), 2**10); "
    "không phải chỗ chạy code Python tùy ý. "
    "Không dùng để giải phương trình (calc_solve), đạo hàm/tích phân, hay % đổi (calc_percent_change)."
)

CALC_EVALUATE_EXPRESSION = (
    "string (bắt buộc) - Biểu thức toán cần tính (ví dụ: 2*(10+5)/3 hoặc sqrt(2))."
)
CALC_EVALUATE_NUMERIC = (
    "boolean (tùy chọn) - true kèm kết quả số thực; false chỉ symbolic (mặc định true)."
)

# ---------------------------------------------------------------------------
# name: calc_solve
# ---------------------------------------------------------------------------
CALC_SOLVE = (
    "Giải phương trình theo một ẩn bằng SymPy.\n"
    "Dùng khi người dùng hỏi nghiệm của phương trình hoặc biểu thức bằng 0.\n"
    "Input: equation (bắt buộc); variable (tùy chọn, mặc định x).\n"
    "Output: JSON gồm equation, variable, solutions, solutions_numeric.\n"
    "Lưu ý: có thể viết 'x**2 - 4', 'x**2 - 4 = 0', hoặc '2*x + 1 = 5'. "
    "Hệ nhiều ẩn / phương trình rất phức tạp có thể không giải được."
)

CALC_SOLVE_EQUATION = (
    "string (bắt buộc) - Phương trình cần giải "
    "(ví dụ: 'x**2 - 4', 'x**2 - 4 = 0', '2*x + 1 = 5')."
)
CALC_SOLVE_VARIABLE = "string (tùy chọn) - Ẩn số cần giải (mặc định x)."

# ---------------------------------------------------------------------------
# name: calc_diff
# ---------------------------------------------------------------------------
CALC_DIFF = (
    "Đạo hàm biểu thức theo một biến bằng SymPy.\n"
    "Dùng khi cần đạo hàm symbolic (kể cả bậc cao) để giải bài hoặc kiểm tra.\n"
    "Input: expression (bắt buộc); variable, order (tùy chọn).\n"
    "Output: JSON gồm expression, variable, order, symbolic, latex.\n"
    "Lưu ý: order từ 1 đến 5. Không dùng cho tích phân (calc_integrate)."
)

CALC_DIFF_EXPRESSION = (
    "string (bắt buộc) - Biểu thức cần đạo hàm (ví dụ: x**3 + 2*x)."
)
CALC_DIFF_VARIABLE = "string (tùy chọn) - Biến đạo hàm (mặc định x)."
CALC_DIFF_ORDER = "integer (tùy chọn) - Bậc đạo hàm từ 1 đến 5 (mặc định 1)."

# ---------------------------------------------------------------------------
# name: calc_integrate
# ---------------------------------------------------------------------------
CALC_INTEGRATE = (
    "Tích phân biểu thức theo một biến bằng SymPy (bất định hoặc có cận).\n"
    "Dùng khi cần nguyên hàm hoặc tích phân xác định chính xác.\n"
    "Input: expression (bắt buộc); variable, lower, upper (tùy chọn).\n"
    "Output: JSON gồm expression, variable, definite, lower, upper, symbolic, latex, numeric.\n"
    "Lưu ý: truyền đủ lower và upper thì tích phân xác định; thiếu thì bất định. "
    "Không phải mọi biểu thức đều có nguyên hàm dạng đóng. Không dùng cho đạo hàm (calc_diff)."
)

CALC_INTEGRATE_EXPRESSION = (
    "string (bắt buộc) - Biểu thức cần tích phân (ví dụ: x**2)."
)
CALC_INTEGRATE_VARIABLE = "string (tùy chọn) - Biến tích phân (mặc định x)."
CALC_INTEGRATE_LOWER = (
    "string (tùy chọn) - Cận dưới (ví dụ: '0'). Cần kèm upper cho tích phân xác định."
)
CALC_INTEGRATE_UPPER = (
    "string (tùy chọn) - Cận trên (ví dụ: '1'). Cần kèm lower cho tích phân xác định."
)

# ---------------------------------------------------------------------------
# name: calc_percent_change
# ---------------------------------------------------------------------------
CALC_PERCENT_CHANGE = (
    "Tính phần trăm thay đổi giữa hai số: ((new - old) / old) * 100.\n"
    "Dùng khi đã có sẵn giá trị cũ và mới và cần % tăng/giảm chính xác.\n"
    "Input: old, new (bắt buộc).\n"
    "Output: JSON gồm old, new, absolute_change, percent_change.\n"
    "Lưu ý: old = 0 sẽ lỗi. Ví dụ old=100, new=120 → percent_change = 20.0."
)

CALC_PERCENT_CHANGE_OLD = (
    "float (bắt buộc) - Giá trị cũ (mẫu số; không được bằng 0)."
)
CALC_PERCENT_CHANGE_NEW = "float (bắt buộc) - Giá trị mới."
