import json, hashlib, pymupdf, re, sys
from decimal import Decimal as D
PDF="pdf/BCTN_2025_ad403f779b.pdf"; doc=pymupdf.open(PDF)
SRC="fpt-ar2025-9449a725"
def ev(qid,n,page,locator,quotes,visual=None):
    pg=doc[page-1]; rects=[]
    for q in quotes:
        r=pg.search_for(q)
        if not r: sys.exit(f"{qid}: quote not found on p{page}: {q!r}")
        rects+=r
    x0=min(r.x0 for r in rects)-6; y0=min(r.y0 for r in rects)-6; x1=max(r.x1 for r in rects)+6; y1=max(r.y1 for r in rects)+6
    e={"id":f"{qid}:E{n}","source_id":SRC,"pdf_page":page,"printed_page":str(page-1),"locator":locator,"quotes":quotes,
       "bbox_pt":[round(max(0,x0),2),round(max(0,y0),2),round(min(pg.rect.width,x1),2),round(min(pg.rect.height,y1),2)],
       "verification":"text_anchor_checked"+("+visual_checked" if visual else "")}
    if visual: e["visual_description"]=visual
    return e
C=[]
def add(cat,q,ans,facts,evs,groups=None,tags=None,calc=None):
    i=len(C)+1; qid=f"FPT-ADVANCED-TEST2-{i:03d}"
    E=[ev(qid,k+1,*e) for k,e in enumerate(evs)]
    c={"id":qid,"suite":"advanced","split":"test2","primary_category":cat,"question":q,"answerable":True,
       "expected_behavior":"search_and_answer","expected_answer":ans,"required_facts":facts,
       "evidence_groups":groups or [{"all_of":[e["id"] for e in E]}],"gold":E,"tags":tags or [cat],
       "grading":{"require_all_facts":True,"require_supported_citations":True,"allow_equivalent_wording":True,"require_units_and_period":True},
       "gold_review_status":"author_checked (Claude, held-out set written before running E2); independent_reviewer_pending"}
    if calc: c["calculations"]=calc
    C.append(c)
def neg(cat,q,missing,related,terms,hits):
    i=len(C)+1; qid=f"FPT-ADVANCED-TEST2-{i:03d}"
    C.append({"id":qid,"suite":"advanced","split":"test2","primary_category":cat,"question":q,"answerable":False,
      "expected_behavior":"search_then_abstain","expected_answer":f"Báo cáo không cung cấp đủ dữ liệu để xác định {missing}.",
      "required_facts":[],"gold":[],"evidence_groups":[],"tags":["insufficient_evidence","near_domain",cat],
      "grading":{"must_explicitly_state_missing_information":True,"must_not_invent_requested_fact":True,"partial_context_allowed_if_supported":True},
      "absence_check":{"missing_information":missing,"related_pdf_pages":related,"full_document_search_terms":terms,"search_hits":hits,
        "method":"Tìm toàn văn 232 trang theo từ khóa và đọc các trang liên quan; từ khóa xuất hiện không có nghĩa thông tin yêu cầu được công bố.",
        "status":"author_checked; independent_reviewer_pending"},
      "gold_review_status":"author_checked (Claude); independent_reviewer_pending"})
def chk(expr,want):
    v=eval(expr,{"D":D}); assert str(v)==want or v==D(want.replace(".","").replace(",",".")), (expr,v,want); return {"expression":expr,"result":want}
# ---------------- table (6)
add("table","Lần phát hành thứ 31 (06/2019) tăng vốn điều lệ theo hình thức nào, tỷ lệ bao nhiêu và vốn điều lệ sau phát hành là bao nhiêu?",
    "Trả cổ tức bằng cổ phiếu theo tỷ lệ 10% từ kết quả kinh doanh năm 2018; vốn điều lệ sau phát hành 6.783.586.880.000 VNĐ.",
    ["trả cổ tức bằng cổ phiếu tỷ lệ 10% từ kết quả kinh doanh năm 2018","vốn điều lệ sau phát hành 6.783.586.880.000 VNĐ"],
    [(35,"Bảng thay đổi vốn điều lệ, lần 31",["6.783.586.880.000","10% từ kết quả kinh doanh năm 2018"])])
add("table","Vốn điều lệ sau lần phát hành tháng 07/2022 tăng bao nhiêu so với sau lần phát hành tháng 05/2022, và lần 07/2022 tăng vốn bằng cách nào?",
    "Tăng 1.828.306.580.000 VNĐ (10.970.265.720.000 − 9.141.959.140.000); lần 07/2022 là trả cổ tức bằng cổ phiếu tỷ lệ 20% từ kết quả kinh doanh năm 2021.",
    ["chênh 1.828.306.580.000 VNĐ","trả cổ tức bằng cổ phiếu 20% từ kết quả kinh doanh năm 2021"],
    [(35,"Bảng thay đổi vốn điều lệ, lần 36 và 37",["9.141.959.140.000","10.970.265.720.000"])],
    calc=[chk("D(10970265720000)-D(9141959140000)","1828306580000")])
add("table","Công ty Cổ phần Công nghệ Y tế FPT có hoạt động chính gì và tỷ lệ sở hữu của FPT tại 31/12/2025 và 31/12/2024 là bao nhiêu?",
    "Xử lý dữ liệu và dịch vụ CNTT; tại 31/12/2025 tỷ lệ sở hữu 99,99% (biểu quyết 99,99%); tại 31/12/2024 công ty chưa thành lập.",
    ["hoạt động chính: xử lý dữ liệu và dịch vụ CNTT","31/12/2025: 99,99%","31/12/2024: chưa thành lập"],
    [(223,"Phụ lục 1, dòng 68",["Công ty Cổ phần Công nghệ Y tế FPT","Xử lý dữ liệu và dịch vụ CNTT"])])
add("table","Tỷ lệ sở hữu của FPT tại Công ty TNHH FPT Smart Cloud Japan thay đổi thế nào giữa 31/12/2024 và 31/12/2025?",
    "Giảm từ 100% (31/12/2024) xuống 60% (31/12/2025); tỷ lệ biểu quyết cũng từ 100% xuống 60%; công ty dịch vụ CNTT tại Nhật Bản.",
    ["31/12/2024: 100%","31/12/2025: 60%","giảm (tỷ lệ biểu quyết cũng 60%)"],
    [(222,"Phụ lục 1, dòng 60",["FPT Smart Cloud Japan"])])
add("table","Theo bảng thành viên HĐQT, ông Hampapur Rangadore Binod có kinh nghiệm chuyên môn gì, bắt đầu là thành viên HĐQT từ ngày nào và tham dự bao nhiêu buổi họp HĐQT năm 2025?",
    "Chuyên môn CNTT; là thành viên HĐQT từ 07/04/2022; tham dự 07/07 buổi họp (100%).",
    ["CNTT","07/04/2022","07/07 buổi họp, 100%"],
    [(87,"Bảng thành viên HĐQT, dòng Hampapur Rangadore Binod",["Hampapur","Rangadore Binod"])])
add("table","Năm 2025, giao dịch vay và trả nợ vay giữa FPT và Công ty TNHH Đầu tư FPT có giá trị bao nhiêu, và số trả nợ lớn hơn số vay bao nhiêu?",
    "Vay 232.000.000.000 VNĐ; trả nợ vay 264.000.000.000 VNĐ; trả nợ lớn hơn vay 32.000.000.000 VNĐ.",
    ["vay 232.000.000.000 VNĐ","trả nợ vay 264.000.000.000 VNĐ","chênh 32.000.000.000 VNĐ"],
    [(96,"Giao dịch với bên liên quan, STT 6 Công ty TNHH Đầu tư FPT",["232.000.000.000","264.000.000.000"])],
    calc=[chk("D(264000000000)-D(232000000000)","32000000000")])
# ---------------- image / diagram (5)
add("image","Trong bảng định hướng và cam kết ESG, vấn đề 'Hoạt động vì môi trường xanh' gắn với tiêu chuẩn GRI nào và cam kết ngắn hạn, dài hạn là gì?",
    "GRI 300 (Môi trường); mục tiêu ngắn hạn đến năm 2030 giảm 15,8% tổng lượng khí thải khí nhà kính; mục tiêu dài hạn đến năm 2040 là Net Zero.",
    ["GRI 300","đến 2030 giảm 15,8% tổng lượng khí thải khí nhà kính","đến 2040 Net Zero"],
    [(113,"Ma trận ESG–GRI, cột Hoạt động vì môi trường xanh",["giảm 15,8%","Net Zero"],"Bảng/ma trận: cột 'Hoạt động vì môi trường xanh' có thẻ GRI 300 Môi trường và hai cam kết ngắn hạn/dài hạn.")])
add("image","Trong bảng định hướng ESG, vấn đề 'Tạo môi trường làm việc đẳng cấp, hạnh phúc' gắn với những tiêu chuẩn GRI nào và có những cam kết nào?",
    "GRI 200 (Kinh tế) và GRI 400 (Xã hội); cam kết: Nơi làm việc hạnh phúc; Tổ chức học tập suốt đời; Bình đẳng và đa dạng.",
    ["GRI 200 và GRI 400","Nơi làm việc hạnh phúc","Tổ chức học tập suốt đời","Bình đẳng và đa dạng"],
    [(113,"Ma trận ESG–GRI, cột Tạo môi trường làm việc đẳng cấp, hạnh phúc",["Nơi làm việc hạnh phúc","Tổ chức học tập suốt đời","Bình đẳng và đa dạng"],"Cột thứ hai của ma trận có hai thẻ GRI 200 (Kinh tế) và GRI 400 (Xã hội) cùng ba cam kết.")])
add("image","Theo infographic Khối Viễn thông, FPT có bao nhiêu trung tâm dữ liệu đạt chuẩn Uptime Tier III quốc tế, dung lượng hạ tầng kết nối quốc tế bao nhiêu và có hạ tầng viễn thông tại bao nhiêu tỉnh, thành?",
    "04 trung tâm dữ liệu đạt chuẩn Uptime Tier III quốc tế; 6.800 Gbps dung lượng hạ tầng kết nối quốc tế; 34 tỉnh, thành có hạ tầng viễn thông và mạng lưới cung cấp dịch vụ.",
    ["04 trung tâm dữ liệu Tier III","6.800 Gbps","34 tỉnh, thành"],
    [(69,"Infographic Khối Viễn thông",["Uptime Tier III quốc tế","kết nối quốc tế"],"Ô số liệu: 04 trung tâm dữ liệu, 6.800Gbps, 34 tỉnh thành trên bản đồ.")])
add("image","Theo infographic về HĐQT, có bao nhiêu thành viên HĐQT độc lập, bao nhiêu thành viên có kinh nghiệm chuyên sâu trong lĩnh vực CNTT và bao nhiêu thành viên có kinh nghiệm chuyên sâu trong lĩnh vực tài chính?",
    "03 thành viên độc lập; 05 thành viên có kinh nghiệm chuyên sâu CNTT; 01 thành viên có kinh nghiệm chuyên sâu tài chính.",
    ["03 độc lập","05 CNTT","01 tài chính"],
    [(88,"Infographic thành phần HĐQT",["Thành viên HĐQT độc lập","trong lĩnh vực tài chính"],"Ô số: 03 độc lập, 01 nữ, 05 CNTT, 01 đầu tư–quản trị, 01 tài chính.")])
add("image","Theo infographic Lĩnh vực Giáo dục, FPT có bao nhiêu đối tác quốc tế, đến từ bao nhiêu quốc gia và có cơ sở đào tạo tại bao nhiêu tỉnh thành?",
    "180 đối tác quốc tế từ 40 quốc gia; cơ sở đào tạo tại 19/34 tỉnh thành.",
    ["180 đối tác quốc tế","40 quốc gia","19/34 tỉnh thành"],
    [(73,"Infographic Lĩnh vực Giáo dục",["Tỉnh thành có cơ sở đào tạo","Quốc gia"],"Ô số: 180 đối tác quốc tế từ 40 quốc gia; 19/34 tỉnh thành có cơ sở đào tạo.")])
# ---------------- chart (5)
add("chart","Theo biểu đồ Doanh thu từ Dịch vụ AI/Data Analytics, doanh thu năm 2025 tăng bao nhiêu tỷ VNĐ so với năm 2024?",
    "Tăng 756 tỷ VNĐ, từ 1.856 tỷ VNĐ (2024) lên 2.612 tỷ VNĐ (2025).",["2024: 1.856 tỷ VNĐ","2025: 2.612 tỷ VNĐ","tăng 756 tỷ VNĐ"],
    [(65,"Biểu đồ cột Doanh thu từ Dịch vụ AI/Data Analytics, cột 2024/2025",["Doanh thu từ Dịch vụ AI/Data Analytics","1.856","2.612"],"Cột 2022–2025: 980; 1.221; 1.856; 2.612; đơn vị tỷ VNĐ.")],
    calc=[chk("D(2612)-D(1856)","756")])
add("chart","Theo biểu đồ Doanh thu từ Dịch vụ AI/Data Analytics, doanh thu năm 2025 gấp khoảng bao nhiêu lần năm 2022?",
    "Khoảng 2,67 lần (2.612 / 980 tỷ VNĐ).",["2022: 980 tỷ VNĐ","2025: 2.612 tỷ VNĐ","≈ 2,67 lần"],
    [(65,"Biểu đồ cột Doanh thu từ Dịch vụ AI/Data Analytics, cột 2022/2025",["980","2.612"],"Cột 2022 = 980, cột 2025 = 2.612 (tỷ VNĐ).")],
    calc=[{"expression":"2612/980","result":"2,665 (≈ 2,67)","tolerance":"±0,01"}])
add("chart","Biểu đồ Quy mô thị trường AI doanh nghiệp ghi giá trị năm 2025 là bao nhiêu và hệ số tăng so với năm 2024 là bao nhiêu?",
    "37,0 tỷ USD năm 2025; tăng 3,2x so với năm 2024 (11,5 tỷ USD).",["37,0 tỷ USD","3,2x so với 2024"],
    [(48,"Biểu đồ đường Quy mô thị trường AI doanh nghiệp, điểm 2025",["Quy mô thị trường AI doanh nghiệp","37,0","3,2x"],"Đường: 2022 0; 2023 1,7; 2024 11,5 (6,8x); 2025 37,0 (3,2x); đơn vị tỷ USD.")])
add("chart","Theo biểu đồ Tỷ lệ số hoá tài liệu, tỷ lệ văn bản phát hành điện tử năm 2023 và năm 2024 là bao nhiêu, tăng bao nhiêu điểm phần trăm?",
    "17,6% (2023) lên 78,9% (2024), tăng 61,3 điểm phần trăm.",["2023: 17,6%","2024: 78,9%","+61,3 điểm phần trăm"],
    [(152,"Biểu đồ Tỷ lệ số hoá tài liệu 2022-2025, cột xanh 2023/2024",["Tỷ lệ số hoá tài liệu giai đoạn 2022-2025","17,6%","78,9%"],"Cột xanh (văn bản điện tử): 7,1%; 17,6%; 78,9%; 95,42%. Cột cam (văn bản cứng): 92,9%; 82,4%; 21,1%; 4,58%.")],
    calc=[chk("D('78.9')-D('17.6')","61,3")])
add("chart","Theo biểu đồ Tỷ lệ các cuộc họp trực tuyến và trực tiếp, tỷ lệ họp trực tiếp năm 2024 và 2025 là bao nhiêu, giảm bao nhiêu điểm phần trăm?",
    "26,8% (2024) xuống 6,0% (2025), giảm 20,8 điểm phần trăm.",["2024: 26,8%","2025: 6,0%","−20,8 điểm phần trăm"],
    [(152,"Biểu đồ thanh ngang họp trực tuyến/trực tiếp 2023-2025, thanh cam 2024/2025",["Tỷ lệ các cuộc họp trực tuyến và trực tiếp","26,8%","6,0%"],"Thanh xanh (trực tuyến): 67,8%; 73,2%; 94,0%. Thanh cam (trực tiếp): 32,2%; 26,8%; 6,0% (2023–2025).")],
    calc=[chk("D('26.8')-D('6.0')","20,8")])
# ---------------- multi-hop (4)
add("multi_hop","Theo thuyết minh hợp nhất kinh doanh và Phụ lục 1, FPT nâng tỷ lệ sở hữu tại Công ty TNHH Ví FPT từ bao nhiêu lên bao nhiêu, và Phụ lục 1 ghi hoạt động chính của công ty này là gì?",
    "Từ 30% lên 100% (Phụ lục 1: 30% tại 31/12/2024, 100% tại 31/12/2025, biểu quyết 100%); hoạt động chính: dịch vụ trung gian thanh toán (thuyết minh: trung gian thanh toán ví điện tử).",
    ["từ 30% lên 100%","dịch vụ trung gian thanh toán"],
    [(189,"Thuyết minh 3 Hợp nhất kinh doanh",["Công ty TNHH Ví FPT","từ 30% lên 100%"]),(223,"Phụ lục 1, dòng 67",["Công ty TNHH Ví FPT","Dịch vụ trung gian thanh toán"])])
add("multi_hop","Kết hợp infographic HĐQT (số thành viên nữ, tổng số thành viên) và tỷ lệ CBNV nữ toàn Tập đoàn năm 2025: tỷ lệ nữ trong HĐQT là bao nhiêu và chênh bao nhiêu điểm phần trăm so với tỷ lệ CBNV nữ?",
    "HĐQT có 01 nữ / 7 thành viên ≈ 14,3%; CBNV nữ chiếm 37,7% tổng nhân sự; HĐQT thấp hơn khoảng 23,4 điểm phần trăm.",
    ["HĐQT: 1/7 ≈ 14,3%","CBNV nữ 37,7%","chênh ≈ 23,4 điểm phần trăm"],
    [(88,"Infographic HĐQT + đoạn HĐQT gồm bảy thành viên",["Thành viên HĐQT nữ","bảy thành"],"Ô '01 Thành viên HĐQT nữ'."),(122,"Bảng Cán bộ nhân viên, kết quả 2025",["37,7%"])],
    calc=[{"expression":"1/7*100; 37,7 - 14,29","result":"14,29%; 23,41 điểm phần trăm (≈ 23,4)","tolerance":"±0,1"}])
add("multi_hop","Năm 2024, quy mô thị trường AI doanh nghiệp toàn cầu và quy mô thị trường AI tự chủ được báo cáo nêu là bao nhiêu, chênh nhau bao nhiêu tỷ USD?",
    "Thị trường AI doanh nghiệp 11,5 tỷ USD (2024); thị trường AI tự chủ 5,1 tỷ USD (2024); chênh 6,4 tỷ USD.",
    ["AI doanh nghiệp 2024: 11,5 tỷ USD","AI tự chủ 2024: 5,1 tỷ USD","chênh 6,4 tỷ USD"],
    [(48,"Đoạn/biểu đồ thị trường AI doanh nghiệp",["11,5 tỷ USD năm 2024"]),(50,"Đoạn AI-First: thị trường AI tự chủ",["5,1 tỷ USD"])],
    calc=[chk("D('11.5')-D('5.1')","6,4")])
add("multi_hop","Ai là thành viên HĐQT nữ duy nhất của FPT và bà tham dự bao nhiêu buổi họp HĐQT trong năm 2025?",
    "Bà Trần Thị Hồng Lĩnh (Ủy viên HĐQT); tham dự 07/07 buổi họp, tỷ lệ 100%.",
    ["Bà Trần Thị Hồng Lĩnh","07/07 buổi họp (100%)"],
    [(88,"Infographic: 01 thành viên HĐQT nữ",["Thành viên HĐQT nữ"],"Ô '01 Thành viên HĐQT nữ'."),(87,"Bảng thành viên HĐQT, dòng Bà Trần Thị Hồng Lĩnh",["Bà Trần Thị Hồng Lĩnh"])])
# ---------------- text (4)
add("text","Báo cáo ESG trong báo cáo thường niên 2025 là năm thứ mấy FPT thực hiện, kỳ báo cáo là khi nào và tham chiếu bộ tiêu chuẩn nào?",
    "Năm thứ 05; kỳ báo cáo 01/01/2025–31/12/2025, chu kỳ thường niên; tham chiếu GRI Standards của GRI.",
    ["năm thứ 05","01/01/2025-31/12/2025, thường niên","GRI Standards"],
    [(112,"Thông tin chung về báo cáo ESG",["năm thứ 05","01/01/2025-31/12/2025","GRI Standards"])])
add("text","Năm 2025 FPT đã đánh giá CSR bao nhiêu phần trăm nhà cung cấp trọng yếu, và mục tiêu áp dụng chính sách mua sắm bền vững đến năm 2026 là bao nhiêu phần trăm nhà cung cấp trọng yếu?",
    "Đã đánh giá CSR 42% nhà cung cấp trọng yếu (2025); mục tiêu áp dụng chính sách mua sắm bền vững cho 60% nhà cung cấp trọng yếu vào năm 2026.",
    ["2025: đánh giá CSR 42% nhà cung cấp trọng yếu","mục tiêu 60% vào năm 2026"],
    [(117,"Quản trị mua sắm bền vững: mục tiêu và kết quả 2025",["CSR 42%","60% nhà cung"])])
add("text","Đối với phát triển bền vững, khung quản lý rủi ro của FPT xác định bao nhiêu nhóm rủi ro chính và đó là những nhóm nào?",
    "05 nhóm: rủi ro chiến lược; rủi ro hoạt động; rủi ro tài chính; rủi ro luật định; rủi ro môi trường – thiên tai – dịch bệnh.",
    ["05 nhóm","chiến lược, hoạt động, tài chính, luật định, môi trường – thiên tai – dịch bệnh"],
    [(131,"Quản trị rủi ro: 05 nhóm rủi ro chính",["05 nhóm rủi ro chính","Rủi ro chiến lược, Rủi ro hoạt động"])])
add("text","Giải thưởng sáng tạo iKhiến đã triển khai bao nhiêu năm, ghi nhận tổng cộng bao nhiêu sáng kiến, và riêng năm 2025 có bao nhiêu sáng kiến đăng ký với giá trị kinh tế bao nhiêu?",
    "09 năm; tổng 13.227 sáng kiến; năm 2025 có 3.838 sáng kiến đăng ký, giá trị kinh tế gần 1.000 tỷ đồng.",
    ["09 năm","13.227 sáng kiến","2025: 3.838 sáng kiến","gần 1.000 tỷ đồng"],
    [(122,"Chính sách thúc đẩy nghiên cứu, sáng tạo: iKhiến",["13.227","3.838"])])
# ---------------- insufficient evidence (6)
neg("table","Năm 2025, số giải ngân đầu tư của Khối Công nghệ phân theo từng quốc gia/thị trường là bao nhiêu?",
    "giải ngân đầu tư 2025 của Khối Công nghệ theo từng quốc gia/thị trường",[75],["giải ngân"],{"giải ngân":[75]})
neg("table","Doanh thu năm 2025 của Công ty TNHH FPT Taiwan là bao nhiêu?","doanh thu riêng năm 2025 của Công ty TNHH FPT Taiwan",[218],["FPT Taiwan"],{"FPT Taiwan":[218]})
neg("text","FPT đã chi bao nhiêu tiền để sở hữu 10% cổ phần Daythree Digital Berhad?","giá trị khoản đầu tư vào 10% cổ phần Daythree Digital Berhad",[64],["Daythree"],{"Daythree":[64]})
neg("chart","Theo biểu đồ họp trực tuyến/trực tiếp, tỷ lệ họp trực tuyến của FPT năm 2022 là bao nhiêu?","tỷ lệ họp trực tuyến năm 2022 (biểu đồ chỉ có 2023–2025)",[152,148],["họp trực tuyến"],{"họp trực tuyến":[148,152]})
neg("chart","Doanh thu Dịch vụ AI/Data Analytics năm 2025 phân theo từng thị trường (Nhật Bản, Mỹ, châu Âu, APAC) là bao nhiêu?","doanh thu AI/Data Analytics 2025 theo từng thị trường",[65],["AI/Data","Data Analytics"],{"AI/Data":[65],"Data Analytics":[65]})
neg("multi_hop","Kết hợp quy mô thị trường AI doanh nghiệp toàn cầu 2025 và doanh thu AI/Data Analytics của FPT, thị phần chính xác của FPT trên thị trường AI doanh nghiệp toàn cầu năm 2025 là bao nhiêu?",
    "thị phần của FPT trên thị trường AI doanh nghiệp toàn cầu năm 2025 (hai chỉ tiêu khác phạm vi định nghĩa và đơn vị tiền tệ, báo cáo không công bố thị phần này)",[48,65,52],["thị phần","AI doanh nghiệp"],{"thị phần":[52,58,69,70],"AI doanh nghiệp":[48]})
cats={}
for c in C:
    k=c["primary_category"] if c["answerable"] else "insufficient"; cats[k]=cats.get(k,0)+1
print(len(C),cats)
json.dump(C,open("benchmark/fpt_2025/gold/advanced.test2.json","w"),ensure_ascii=False,indent=1)
json.dump([{"id":c["id"],"question":c["question"]} for c in C],open("benchmark/fpt_2025/queries/advanced.test2.json","w"),ensure_ascii=False,indent=1)
for f in ("gold/advanced.test2.json","queries/advanced.test2.json"):
    print(f, hashlib.sha256(open("benchmark/fpt_2025/"+f,"rb").read()).hexdigest())
