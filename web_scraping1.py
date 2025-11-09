from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import csv
import re
import time
import pickle

urls=pickle.load(open("uni_urls", "rb"))
# University URLs
universities = [
    {"name": "VIT-AP", "url": "https://vitap.ac.in/fees-and-scholarships", "state": "Andhra Pradesh"},
    {"name": "Manipal", "url": "https://www.manipal.edu/scholarships", "state": "Karnataka"},
    {"name": "VIT Vellore", "url": "https://vit.ac.in/scholarship", "state": "Tamil Nadu"},
    {"name": "SRM IST", "url": "https://www.srmist.edu.in/policies/scholarship-policy/", "state": "Tamil Nadu"},
    {"name": "SRM AP", "url": "https://srmap.edu.in/financial-aid-and-scholarship/", "state": "Andhra Pradesh"},
    {"name": "Woxsen University", "url": "https://woxsen.edu.in/admissions/scholarship/", "state": "Telangana"},
    {"name": "Malla Reddy University", "url": "https://www.mallareddyuniversity.ac.in/merit-scholarship", "state": "Telangana"},
    {"name": "Jain University", "url": "https://www.jainuniversity.ac.in/academics/scholarships-offered-in-india", "state": "Karnataka"},
    {"name": "Christ University", "url": "https://christuniversity.in/scholarships", "state": "Karnataka"}
]

# Function to clean text
def clean_text(text):
    return re.sub(r'\s+', ' ', text.strip())

# Initialize CSV data and deduplication
all_scholarships = []
seen_scholarships = set()

# Set up Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--user-agent=Mozilla/5.0")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--allow-insecure-localhost")
driver = webdriver.Chrome(service=Service(), options=chrome_options)

try:
    for uni in universities:
        print(f"Scraping {uni['name']}...")
        try:
            driver.get(uni['url'])
            # Scroll and click expandable elements
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                # Click accordions/tabs
                for elem in driver.find_elements(By.CSS_SELECTOR, '[role="button"], .accordion, .toggle, [data-toggle], [class*="expand"]'):
                    try:
                        elem.click()
                        time.sleep(1)
                    except:
                        pass
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            time.sleep(10)  # Final wait
            soup = BeautifulSoup(driver.page_source, 'html.parser')
        except Exception as e:
            print(f"Error fetching {uni['name']}: {e}")
            continue

        # Find scholarship section
        scholarship_section = None
        for tag in ['h1', 'h2', 'h3', 'div', 'section', 'article']:
            scholarship_section = soup.find(tag, string=re.compile(r'scholarship|merit|financial aid|fees|award', re.I)) or \
                                 soup.find(tag, class_=re.compile(r'scholarship|merit|financial|fees|award|item|list', re.I))
            if scholarship_section:
                print(f"Found scholarship section for {uni['name']}: {clean_text(scholarship_section.text)}")
                break

        if not scholarship_section:
            print(f"No scholarship section found for {uni['name']}. Using page-wide search.")
            scholarship_section = soup

        # Extract content
        scholarships = []
        current_scholarship = None
        content = scholarship_section.find_all(['h3', 'h4', 'p', 'li', 'div', 'span', 'table', 'a', 'ul', 'article']) or \
                  soup.find_all(['h3', 'h4', 'p', 'li', 'div', 'span', 'table', 'a', 'ul', 'article'])
        print(f"Found {len(content)} elements for {uni['name']}")

        for element in content:
            text = clean_text(element.text)
            if element.name in ['h3', 'h4'] or \
               (element.name in ['div', 'span', 'article'] and \
                re.search(r'scholarship|merit|freeship|award|GV|Rajeswari|Kalam|EduEmpower|Achiever|Scholar', text, re.I)):
                scholarship_key = f"{uni['name']}_{text.lower()}"
                if scholarship_key in seen_scholarships:
                    print(f"Skipping duplicate scholarship: {text}")
                    current_scholarship = None
                    continue
                if current_scholarship:
                    scholarships.append(current_scholarship)
                current_scholarship = {
                    'state': uni['state'],
                    'university': uni['name'],
                    'name': text,
                    'details': '',
                    'eligibility': '',
                    'amount': '',
                    'deadline': '',
                    'link': uni['url']
                }
                seen_scholarships.add(scholarship_key)
                print(f"Found scholarship: {current_scholarship['name']}")
            elif current_scholarship and element.name in ['p', 'li', 'div', 'span', 'ul', 'article'] and text:
                current_scholarship['details'] += text + ' '
                if re.search(r'\$\d+|₹\d+|up to|worth|waiver|free', text, re.I):
                    current_scholarship['amount'] += text + ' '
                if re.search(r'eligible|criteria|requirement|rank|cgpa|score|marks|topper', text, re.I):
                    current_scholarship['eligibility'] += text + ' '
                if re.search(r'deadline|apply by|closing|\d{1,2}/\d{1,2}/\d{4}', text, re.I):
                    current_scholarship['deadline'] += text + ' '
            elif current_scholarship and element.name == 'table':
                rows = element.find_all('tr')
                for row in rows:
                    cells = [clean_text(cell.text) for cell in row.find_all(['td', 'th'])]
                    current_scholarship['details'] += ' | '.join(cells) + ' '
            elif current_scholarship and element.name == 'a' and element.get('href'):
                href = element.get('href')
                if 'apply' in href.lower() or 'scholarship' in href.lower():
                    current_scholarship['link'] = href if href.startswith('http') else uni['url'].rstrip('/') + '/' + href.lstrip('/')

        if current_scholarship:
            scholarships.append(current_scholarship)

        if not scholarships:
            print(f"No scholarships extracted for {uni['name']}. Check HTML structure or dynamic content.")
        else:
            print(f"Extracted {len(scholarships)} scholarships for {uni['name']}")

        all_scholarships.extend(scholarships)

finally:
    driver.quit()

# pickle.dump(all_scholarships, open("all_scholarships", "wb"))
# pickle.load(open("all_scholarships", "rb"))
# Remove duplicates based on name and university
# Save to CSV
csv_file = "scholarships.csv"
with open(csv_file, 'w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=['state','university', 'name', 'details', 'eligibility', 'amount', 'deadline', 'link'])
    writer.writeheader()
    writer.writerows(all_scholarships)

print(f"Data saved to {csv_file}")
print(f"Total scholarships collected: {len(all_scholarships)}")