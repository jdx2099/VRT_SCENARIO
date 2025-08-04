import csv
import os
import re
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# --- 配置 ---
CSV_FILE_PATH = "functional_modules_output_v2.csv"
PERSIST_DIRECTORY = "db_chroma"

def load_modules_from_csv(csv_filepath):
    """从CSV文件加载功能模块并转换为LangChain Document对象。"""
    documents = []
    try:
        with open(csv_filepath, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames or not all(field in reader.fieldnames for field in ["id", "功能模块名称", "功能模块描述"]):
                print(f"错误: CSV文件 '{csv_filepath}' 缺少必要的列标题 (id, 功能模块名称, 功能模块描述)。")
                return []

            for row_num, row in enumerate(reader, 1):
                module_id = row.get("id", "").strip()
                module_name = row.get("功能模块名称", "").strip()
                module_description = row.get("功能模块描述", "").strip()

                if not module_id or not module_name or not module_description:
                    print(f"警告: CSV文件第 {row_num} 行数据不完整，已跳过。")
                    continue
                
                page_content = f"功能名称：{module_name}\n功能描述：{module_description}"
                metadata = {"id": module_id, "功能模块名称": module_name, "原始描述": module_description}
                doc = Document(page_content=page_content, metadata=metadata)
                documents.append(doc)
            print(f"从 '{csv_filepath}' 文件中成功加载了 {len(documents)} 个功能模块。")
    except FileNotFoundError:
        print(f"错误: CSV文件 '{csv_filepath}' 未找到。")
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")
    return documents

# --- 主脚本执行 ---

# 1. 初始化 Embedding 模型
print("正在初始化Embedding模型...")
try:
    embeddings = OpenAIEmbeddings(
        openai_api_base="http://127.0.0.1:9997/v1",
        openai_api_key="EMPTY",
        model="Qwen3-Embedding-8B-local"
    )
    print("Embedding模型初始化成功。")
except Exception as e:
    print(f"初始化Embedding模型失败: {e}")
    exit()

# 2. 创建或加载向量存储
vector_store = None
if os.path.exists(PERSIST_DIRECTORY):
    print(f"检测到已存在的数据库，正在从 '{PERSIST_DIRECTORY}' 加载...")
    try:
        vector_store = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)
        print("✅ 向量数据库加载成功！")
    except Exception as e:
        print(f"加载数据库失败: {e}。将尝试重新创建。")
else:
    print(f"未找到本地数据库，将创建新的数据库并持久化到 '{PERSIST_DIRECTORY}'...")
    all_documents_from_csv = load_modules_from_csv(CSV_FILE_PATH)
    if not all_documents_from_csv:
        print("未能从CSV加载任何文档，程序将退出。")
        exit()

    print(f"正在创建新的向量存储，并将 {len(all_documents_from_csv)} 个文档添加进去...")
    try:
        vector_store = Chroma.from_documents(
            documents=all_documents_from_csv,
            embedding=embeddings,
            persist_directory=PERSIST_DIRECTORY
        )
        print("✅ 新的向量数据库创建并保存成功！")
    except Exception as e:
        print(f"创建向量数据库时出错: {e}")
        exit()

# 3. 执行相似度搜索
if not vector_store:
    print("向量库未能成功加载或创建，无法进行搜索。")
    exit()

user_review_full_text = """
【最满意的一点】
满意的地方挺多的，先说一下车子的外观吧，属于那种比较大气的感觉，前脸设计的也很时尚，用了一个家族式的设计，觉得比亚迪的唐还是很有辨识度的，空间的表现也挺让我满意的，车子里很宽敞，坐着就很舒服，这就是动力挺强的，买了就跑了一次高速，一开始新车还不舍得给油，后来整个人就来感觉了，百公里加速特别快，动力一点都没有迟钝，颜色方面没有选择常见的白色，因为感觉黑色特别的威武霸道
【最不满意的一点】
不太满意的地方就是车里的味道吧，刚提车的时候就感觉有一些大的，现在已经很久了，还是有一点点味道
【空间】

空间：比亚迪唐前排的视野非常的宽阔，后排也挺宽敞的，做后排的人都可以任意的活动，我们一家人都挺满意的，一点都不会有憋屈感，自己平时带着家里人出去，或者接送客户，都没有太大的问题，空间挺实用的
☆ 第三排空间：买的这段时间很少坐满七个人的情况，所以第三排大部分时间都是放倒的情况，这样可以充分把空间利用起来
【动力】

动力：动力方面，加速很快，电机驱动还是很有力量的，生产油门之后的提速感非常过瘾，爆发力强劲，动力的持续性也很不错，市区的时候堵车的情况也不会有任何的顿挫感，超车和爬坡就更不在话下，完全可以轻松的应对
【操控】

操控：方向盘的设计还是挺有特色的，手感很舒服，转弯的时候也比较稳，没有虚位挺精准的，车里的视线也特别好，还有挺多的辅助驾驶功能，平时开车的话挺方便的，比较省心操控很容易上手
【油耗】

能耗：纯电平时能开出70到80公里的样子，能耗这一方面在我的接受范围里，有这么大一台车，我已经比较满意了
【舒适性】

舒适性：市区里头路况不是很好，有挺多坑洼的路段，然后悬架的表现还是不错的，调教的很好，软硬程度适中，缺点就是很长一段时间，车内的异味有点大
【外观】

外观：前面的设计是一个家族语言很耐看，格栅的造型比较有气势，大灯犀利有神，车身的线条很流畅，充满着肌肉感，车子足够的年轻化，不会显得老气
【内饰】

内饰：内饰设计真的特别时尚，全液晶的仪表盘很科技化，座椅是真皮的软硬程度适中，电子档把厚实有力，整个车的内饰做工和用料都值得认可，很豪华
【性价比】

性价比：性价比方面，比亚迪唐可以说很实在了，这样的价位里面配置空间动力都比较全面，整个买车的过程还是比较愉快的，销售服务很到位，比亚迪这个品牌的质量不用多说，三电系统保终身，有底气
【为什么最终选择这款车】
节能减排应该是一个大势所趋，所以买新车果断选择了新能源汽车，选择这款车的原因主要是它的品牌吧，比亚迪的技术还是比较深入人心的，在这个价位的SUV里面，对比了一下，动力空间配置，感觉比亚迪唐的性价比还是挺高的，而且我觉得这款车子的颜值还是很高的，以后的养车成本算下来还是比较划算
"""

def split_review_into_queries(review_text):
    """仅按【章节】拆分评论，每个章节内容作为一个完整的查询。"""
    queries = []
    sections = re.split(r'(【[^】]+】)', review_text)
    
    current_section_title = "评论开头"
    for part in sections:
        part = part.strip()
        if not part:
            continue
        
        if part.startswith("【") and part.endswith("】"):
            current_section_title = part
        else:
            query_text = part
            if len(query_text) > 5:
                queries.append({"source_section": current_section_title, "query_text": query_text})
                
    return queries


generated_queries = split_review_into_queries(user_review_full_text)
print(f"\n按章节拆分，共生成了 {len(generated_queries)} 条查询:")

SCORE_THRESHOLD = 1.0

for item in generated_queries:
    section_title = item["source_section"]
    query_text = item["query_text"]
    print(f"\n--- 正在搜索与章节 '{section_title}' 相关的功能模块 ---")
    
    # --- 新增打印 ---
    # 打印当前用于搜索的实际文本内容（预览）
    print(f"  查询内容: \"{query_text[:80]}...\"")
    
    try:
        results_with_scores = vector_store.similarity_search_with_score(query_text, k=1)
        
        if results_with_scores:
            doc, score = results_with_scores[0]
            
            if score < SCORE_THRESHOLD:
                print(f"  ✅ 找到1个高相关度模块 (分数: {score:.4f}):")
                print(f"    - ID: {doc.metadata.get('id', 'N/A')}")
                print(f"    - 功能模块名称: {doc.metadata.get('功能模块名称', 'N/A')}")
                print(f"    - 相关描述片段: {doc.page_content[:100]}...")
            else:
                print(f"  ❌ 找到1个模块，但相关度过低 (分数: {score:.4f} >= {SCORE_THRESHOLD})，已忽略。")
        else:
            print("  未能找到任何相关的功能模块。")
            
    except Exception as e:
        print(f"  执行查询时出错: {e}")