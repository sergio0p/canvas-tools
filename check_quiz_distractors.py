import requests
import keyring
import json

SERVICE_NAME = 'canvas'
USERNAME = 'access-token'
HOST = 'https://uncch.instructure.com'
COURSE_ID = 97934
ASSIGNMENT_ID = 759239

token = keyring.get_password(SERVICE_NAME, USERNAME)
headers = {'Authorization': f'Bearer {token}'}

# Step 1: Fetch quiz metadata
quiz_url = f"{HOST}/api/quiz/v1/courses/{COURSE_ID}/quizzes/{ASSIGNMENT_ID}"
quiz_response = requests.get(quiz_url, headers=headers)

if quiz_response.status_code != 200:
    print(f"❌ Quiz metadata failed: {quiz_response.status_code}")
    print(quiz_response.text)
    exit()

quiz_data = quiz_response.json()
print("✅ Got quiz metadata")

# Step 2: Fetch quiz items/questions
items_url = f"{quiz_url}/items"
items_response = requests.get(items_url, headers=headers)

if items_response.status_code != 200:
    print(f"❌ Items fetch failed: {items_response.status_code}")
    print(items_response.text)
    quiz_data['items'] = []
else:
    items = items_response.json()
    quiz_data['items'] = items
    print(f"✅ Got {len(items)} item(s)")

# Save combined data
with open('quiz_759239_complete.json', 'w') as f:
    json.dump(quiz_data, indent=2, fp=f)

print("\n✅ Saved to quiz_759239_complete.json")

# Analyze categorization questions
if quiz_data.get('items'):
    for item in quiz_data['items']:
        if item.get('entry', {}).get('interaction_type_slug') == 'categorization':
            print(f"\n🎯 Categorization Question: {item['id']}")
            
            interaction_data = item['entry']['interaction_data']
            scoring_data = item['entry']['scoring_data']
            
            categories = interaction_data.get('categories', {})
            distractors = interaction_data.get('distractors', {})
            
            # Count items that need classification
            items_to_classify = set()
            for cat in scoring_data.get('value', []):
                items_to_classify.update(cat['scoring_data']['value'])
            
            num_distractors = len(distractors)
            num_to_classify = len(items_to_classify)
            
            print(f"  Categories: {len(categories)}")
            print(f"  Items in 'distractors' field: {num_distractors}")
            print(f"  Items needing classification: {num_to_classify}")
            
            if num_to_classify < num_distractors:
                num_true_distractors = num_distractors - num_to_classify
                print(f"\n  ⚠️  TRUE DISTRACTORS FOUND: {num_true_distractors}")
                
                # Identify which are true distractors
                distractor_uuids = set(distractors.keys())
                true_distractor_uuids = distractor_uuids - items_to_classify
                
                print(f"  True distractor items:")
                for uuid in true_distractor_uuids:
                    print(f"    - {distractors[uuid]['item_body']}")
            else:
                print(f"\n  ✅ No true distractors - all items need classification")
else:
    print("\n⚠️  Quiz has no items/questions")