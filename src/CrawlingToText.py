import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# 크롬 드라이버 설정
options = Options()
options.add_argument('--headless')
options.add_argument("--window-size=1920x1080")
driver = webdriver.Chrome(options=options)

driver.get("https://roadmap.sh/")
time.sleep(3)

roadmapData = []

# 각 색션 찾기
sections = driver.find_elements(By.XPATH,"//h2")

for section in sections:
    roadmapType = section.text.strip()
    #'Questions'까지만 수집
    if roadmapType == 'Questions':
        break

    #색션 다음 요소에서 항목 추출
    nextDiv = section.find_element(By.XPATH,"following-sibling::*[1]")

    links = nextDiv.find_elements(By.TAG_NAME,"a")
    for link in links:
        roadmapName = link.text.strip()

        #'New'가 포함되어 있다면 괄호로 감싸기
        if roadmapName.endswith("New"):
            roadmapName = roadmapName.replace("New", "").strip()

        if roadmapName:
            roadmapData.append({
                'roadmapType': roadmapType,
                'roadmapName': roadmapName,
            })

#종료
driver.quit()

# 데이터프레임 변환 및 저장
df = pd.DataFrame(roadmapData)

# roadmapName을 URL에 사용할 수 있도록 변환
df['urlName'] = df['roadmapName'].str.lower().str.replace(' ', '-').str.replace(r'[^\w\-]', '', regex=True)

# 예외 처리 매핑 사전
exceptionMapping = {
    "ai-and-data-scientist": "ai-data-scientist",
    "postgresql": "postgresql-dba",
    "developer-relations": "devrel",
    "c": "cpp",
    "go-roadmap": "golang",
    "design-and-architecture": "software-design-architecture",
    "data-structures--algorithms": "datastructures-and-algorithms",
    "git-and-github": "git-github"
}

# 매핑 적용
df['urlName'] = df['urlName'].apply(lambda x: exceptionMapping.get(x, x))

def GetRoadmapDf():
    return df