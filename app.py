import streamlit as st
import os
import shutil
import pdfplumber
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn
from nltk.stem import WordNetLemmatizer
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from collections import Counter
from datetime import datetime, timedelta
import pymysql
import re
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

# Define a directory to store uploaded files
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Check Streamlit version
if st.__version__ < "0.84.0":
    st.error("Streamlit version 0.84.0 or higher is required. Please upgrade Streamlit using 'pip install --upgrade streamlit'.")
    st.stop()

# Download required NLTK resources
try:
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')
    nltk.download('wordnet')
    nltk.download('averaged_perceptron_tagger_eng')
    nltk.download('vader_lexicon')
except Exception as e:
    st.error(f"Failed to download NLTK resources: {e}")
    st.stop()

# Initialize NLTK tools
lemmatizer = WordNetLemmatizer()
sid = SentimentIntensityAnalyzer()

# PyMySQL configuration using environment variables
db_config = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "nut@2003"),
    "database": os.getenv("MYSQL_DATABASE", "Sentisample")
}

# Email configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_USER = os.getenv("EMAIL_USER", "hariman006355@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "oexx yljl ptgy yvxv")

# Define department_incharge dictionary
department_incharge = {
    "Adi Dravidar and Tribal Welfare Department (ADW)": {"name": "Amit Sharma", "id": "ADW001"},
    "Agriculture and Farmers Welfare Department (AGRI)": {"name": "Priya Singh", "id": "AGRI002"},
    "Animal Husbandry and Dairying and Fisheries and Fishermen Welfare Department (AHFISH)": {"name": "Rahul Verma", "id": "AHFISH003"},
    "BC MBC and Minorities Welfare Department (BCMBC)": {"name": "Sneha Gupta", "id": "BCMBC004"},
    "Co-operation Food and Consumer Protection Department (FOODCO)": {"name": "Vikram Patel", "id": "FOODCO005"},
    "Commercial Taxes and Registration Department (CTREG)": {"name": "Anjali Rao", "id": "CTREG006"},
    "Energy Department (ENERGY)": {"name": "Kiran Desai", "id": "ENERGY007"},
    "Environment Climate Change and Forests Department (ENVFOR)": {"name": "Ravi Kumar", "id": "ENVFOR008"},
    "Finance Department (FIN)": {"name": "Neha Joshi", "id": "FIN009"},
    "Handlooms Handicrafts Textiles and Khadi Department (HHTK)": {"name": "Suresh Menon", "id": "HHTK010"},
    "Health and Family Welfare Department (HEALTH)": {"name": "Dr. Anil Kapoor", "id": "HEALTH011"},
    "Higher Education Department (HIGHEDU)": {"name": "Prof. Meera Nair", "id": "HIGHEDU012"},
    "Highways and Minor Ports Department (HWY)": {"name": "Arjun Reddy", "id": "HWY013"},
    "Human Resources Management Department (PAR)": {"name": "Shalini Iyer", "id": "PAR014"},
    "Home Prohibition and Excise Department (HOMEEXC)": {"name": "Inspector Rajesh", "id": "HOMEEXC015"},
    "Housing and Urban Development Department (HUD)": {"name": "Deepak Shah", "id": "HUD016"},
    "Industries Department (IND)": {"name": "Manish Aggarwal", "id": "IND017"},
    "Information Technology Department (IT)": {"name": "Sonia Malhotra", "id": "IT018"},
    "Labour Welfare and Skill Development Department (LBREMP)": {"name": "Vivek Chawla", "id": "LBREMP019"},
    "Law Department (LAW)": {"name": "Advocate Priyanka", "id": "LAW020"},
    "Legislative Assembly Department (LEGIS)": {"name": "MLA Sanjay", "id": "LEGIS021"},
    "Micro Small and Medium Enterprises Department (MSME)": {"name": "Rohit Bansal", "id": "MSME022"},
    "Municipal Administration and Water Supply Department (MAWS)": {"name": "Officer Lakshmi", "id": "MAWS023"},
    "Public Elections Department (ELECTION)": {"name": "Election Officer Vinod", "id": "ELECTION024"},
    "Public Department (PUBLIC)": {"name": "Clerk Ramesh", "id": "PUBLIC025"},
    "Public Works Department (PWD)": {"name": "Engineer Suman", "id": "PWD026"},
    "Revenue and Disaster Management Department (REV)": {"name": "Collector Aruna", "id": "REV027"},
    "Rural Development and Panchayat Raj Department (RDPR)": {"name": "Panchayat Head Mohan", "id": "RDPR028"},
    "School Education Department (SCHOOL)": {"name": "Principal Geeta", "id": "SCHOOL029"},
    "Social Welfare and Women Empowerment Department (SWNM)": {"name": "Officer Shanti", "id": "SWNM030"},
    "Tamil Dev. and Information Department (TAMINF)": {"name": "Director Karthik", "id": "TAMINF031"},
    "Tourism Culture and Religious Endowments Department (TOURCUL)": {"name": "Curator Anil", "id": "TOURCUL032"},
    "Transport Department (TRANS)": {"name": "Transport Officer Sunil", "id": "TRANS033"},
    "Welfare of Differently Abled Persons (DIFFABLE)": {"name": "Coordinator Rekha", "id": "DIFFABLE034"},
    "Youth Welfare and Sports Development Department (YOUTHSP)": {"name": "Coach Vikram", "id": "YOUTHSP035"},
    "Water Resources Department (WRD)": {"name": "Engineer Priya", "id": "WRD036"},
    "Planning Development Department (PLGDEV)": {"name": "Planner Rohan", "id": "PLGDEV037"},
    "Special Programme Implementation (SPI)": {"name": "Coordinator Nisha", "id": "SPI038"}
}

# Define keyword lists for all departments
adw_base = ["tribal", "adi_dravidar", "welfare", "indigenous", "community", "reservation", "scholarship", "housing", "education", "employment", "upliftment", "social_justice", "discrimination", "development", "tribe", "minority", "aid", "support", "backward", "rural",
            "colony_infrastructure", "borewell", "atrocities", "brick_kiln", "burial_ground", "chicken_unit", "cleanliness", "community_hall", "complaint_officer", "e_patta", "employee_grievance", "entrepreneur_scheme", "solar_dryer", "power_supply", "forest_rights", "free_bicycle", "house_patta", "garments", "leather", "higher_education", "hostel", "incentive", "phd", "inter_caste_marriage", "iron_box", "land_purchase", "law_graduate", "livelihood_loan", "milch_animal", "overseas_scholarship", "petty_shop", "policy", "power_tiller", "genuiness_verification", "tnpsc_coaching", "skill_development"]
agri_base = ["agriculture", "farmer", "crop", "irrigation", "subsidy", "fertilizer", "seed", "pesticide", "farming", "soil", "yield", "harvest", "tractor", "insurance", "market", "loan", "drought", "flood", "organic", "horticulture"]
ahfish_base = ["animal", "husbandry", "fishery", "livestock", "dairy", "poultry", "fish", "aquaculture", "veterinary", "milk", "egg", "meat", "fishing", "boat", "net", "welfare", "disease", "vaccination", "breeding"]
bcmbc_base = ["backward", "most_backward", "minority", "welfare", "scholarship", "education", "employment", "housing", "reservation", "social", "community", "development", "aid", "support"]
foodco_base = ["food", "ration", "consumer", "protection", "cooperative", "supply", "grain", "subsidy", "market", "price", "distribution", "card", "shop", "quality", "complaint"]
ctreg_base = ["tax", "commercial", "registration", "gst", "vat", "property", "stamp", "duty", "vehicle", "license", "compliance", "audit", "revenue"]
energy_base = ["energy", "electricity", "power", "solar", "wind", "grid", "bill", "connection", "outage", "renewable", "subsidy", "meter", "transmission"]
envfor_base = ["environment", "climate", "forest", "pollution", "wildlife", "conservation", "tree", "river", "air", "water", "waste", "green", "biodiversity"]
fin_base = ["finance", "budget", "fund", "loan", "grant", "tax", "revenue", "expenditure", "audit", "policy", "subsidy", "investment", "debt"]
hhtk_base = ["handloom", "handicraft", "textile", "khadi", "weaving", "artisan", "craft", "market", "subsidy", "training", "design", "export"]
health_base = ["health", "hospital", "doctor", "medicine", "clinic", "disease", "vaccination", "surgery", "insurance", "sanitation", "maternal", "child", "emergency"]
highedu_base = ["education", "university", "college", "scholarship", "degree", "research", "faculty", "admission", "exam", "curriculum", "infrastructure"]
hwy_base = ["highway", "road", "bridge", "port", "transport", "construction", "maintenance", "traffic", "toll", "safety", "infrastructure"]
par_base = ["human", "resource", "employment", "recruitment", "training", "promotion", "salary", "pension", "grievance", "policy", "staff"]
homeexc_base = ["home", "prohibition", "excise", "police", "crime", "liquor", "safety", "security", "law", "enforcement", "license"]
hud_base = ["housing", "urban", "development", "slum", "apartment", "plot", "construction", "sanitation", "water", "sewerage", "planning"]
ind_base = ["industry", "factory", "manufacturing", "investment", "policy", "license", "export", "production", "infrastructure", "technology"]
it_base = ["information", "technology", "digital", "software", "hardware", "internet", "data", "cyber", "security", "startup", "innovation"]
lbremp_base = ["labour", "welfare", "skill", "employment", "worker", "factory", "wage", "training", "safety", "union", "job"]
law_base = ["law", "legal", "court", "justice", "lawyer", "case", "judgment", "rights", "policy", "dispute", "advocate"]
legis_base = ["legislative", "assembly", "law", "policy", "bill", "mla", "government", "session", "debate", "resolution"]
msme_base = ["micro", "small", "medium", "enterprise", "business", "startup", "loan", "subsidy", "market", "training", "export"]
maws_base = ["municipal", "water", "supply", "sanitation", "sewerage", "road", "street", "waste", "tax", "infrastructure", "urban"]
election_base = ["election", "vote", "polling", "voter", "candidate", "ballot", "campaign", "booth", "registration", "id"]
public_base = ["public", "service", "administration", "grievance", "policy", "welfare", "citizen", "office", "complaint", "support"]
pwd_base = ["public", "works", "construction", "road", "bridge", "building", "maintenance", "project", "infrastructure", "contract"]
rev_base = ["revenue", "disaster", "management", "land", "tax", "record", "patta", "relief", "flood", "earthquake", "aid"]
rdpr_base = ["rural", "development", "panchayat", "village", "road", "water", "sanitation", "housing", "employment", "scheme"]
school_base = ["school", "education", "teacher", "student", "curriculum", "exam", "infrastructure", "scholarship", "uniform", "midday_meal"]
swnm_base = ["social", "welfare", "women", "empowerment", "child", "marriage", "safety", "scheme", "education", "health"]
taminf_base = ["tamil", "development", "information", "culture", "language", "media", "press", "publication", "heritage"]
tourcul_base = ["tourism", "culture", "religious", "endowment", "temple", "festival", "heritage", "travel", "monument", "event"]
trans_base = ["transport", "bus", "train", "road", "vehicle", "license", "ticket", "traffic", "safety", "infrastructure"]
diffable_base = ["disability", "welfare", "aid", "equipment", "education", "employment", "accessibility", "scheme", "support", "health"]
youthsp_base = ["youth", "sport", "welfare", "training", "game", "fitness", "event", "scholarship", "coaching", "facility"]
wrd_base = ["water", "resource", "irrigation", "dam", "river", "canal", "flood", "management", "supply", "conservation"]
plgdev_base = ["planning", "development", "project", "policy", "fund", "infrastructure", "urban", "rural", "growth", "strategy"]
spi_base = ["special", "programme", "implementation", "project", "scheme", "initiative", "task", "fund", "progress", "target", "execution", "monitoring", "development", "priority", "support", "action", "completion", "naan_mudhalvan"]

# Define progress_steps
progress_steps = {
    "Adi Dravidar and Tribal Welfare Department (ADW)": [
        ("Registration and Community Verification", "The complaint is received through the District ADW Office via online portals. The department will verify the complainant’s eligibility by checking community certificates and scheme-specific criteria."),
        ("Scheme-Specific Inquiry", "The complaint is being investigated by the relevant ADW staff."),
        ("Action and Welfare Delivery", "The resolution is currently being executed based on ADW policies."),
        ("Monitoring and Community Feedback", "The complaint is closed after confirming the resolution of the petition.")
    ],
    "Agriculture and Farmers Welfare Department (AGRI)": [
        ("Farmer Registration and Scheme Linkage", "The complaint is received through the Agriculture and Farmers Welfare Department (AGRI) from an online Portal, Kisan Call Center (1800-180-1551), registered with the farmer’s details (Aadhaar-linked Farmer ID from AgriStack) and linked to the specific scheme or service involved, ensuring eligibility and context are verified upfront using the department’s digital infrastructure."),
        ("Field-Level Validation and Data Analysis", "The complaint investigation is being held by local agricultural officers."),
        ("Scheme-Specific Redressal and Disbursement", "A targeted solution is implemented."),
        ("Impact Tracking and Policy Feedback", "The complaint is closed after resolution.")
    ],
    "Animal Husbandry, Dairying, and Fisheries and Fishermen Welfare Department (AHFISH)": [
        ("Livestock/Fishermen Registration", "The complaint is received through the Animal Husbandry, Dairying, and Fisheries and Fishermen Welfare Department (AHFISH) or helplines."),
        ("Field Inspection", "The complaint investigation is being held by Veterinary officers and fisheries inspectors."),
        ("Scheme Execution", "A targeted solution is implemented."),
        ("Monitoring Outcomes", "Complaint is closed after resolution.")
    ],
    "BC, MBC, and Minorities Welfare Department (BCMBC)": [
        ("Community Eligibility Check", "The complaint is received through the department of BC, MBC, and Minorities Welfare (BCMBC)."),
        ("Scheme Record Review", "The complaint investigation is being held by officers and the records are being verified."),
        ("Benefit Disbursal", "A targeted solution is implemented."),
        ("Community Impact Assessment", "Complaint is closed after resolution.")
    ],
    "Co-operation, Food, and Consumer Protection Department (FOODCO)": [
        ("Ration/Consumer Logging", "The complaint is received through the department of Co-operation, Food, and Consumer Protection (FOODCO)."),
        ("Supply Chain Audit", "Fair price shop records or cooperative stock levels are checked to pinpoint shortages or mismanagement."),
        ("Stock Replenishment", "Essential commodities are supplied or consumer grievances redressed and updated."),
        ("Fair Price Oversight", "Complaint is closed after monitoring to ensure uninterrupted food distribution.")
    ],
    "Commercial Taxes and Registration Department (CTREG)": [
        ("Tax/Registration Filing", "The complaint is received through the department of Commercial Taxes and Registration via online portal."),
        ("Record Verification", "Tax officers review payment logs and land records to identify discrepancies."),
        ("Refund or Registration", "Refunds are processed. Documents are issued."),
        ("Tax Compliance Review", "Case is closed, with audits to streamline tax and registration processes.")
    ],
    "Energy Department (ENERGY)": [
        ("Connection Logging", "Complaint is received through the energy department via online portal."),
        ("Grid Assessment", "Engineers inspect substations, lines to diagnose faults and delays in rural electrification."),
        ("Power Restoration", "Electricity is restored or provided."),
        ("Energy Access Review", "Complaint is closed, with data used to improve grid reliability.")
    ],
    "Environment, Climate Change, and Forests Department (ENVFOR)": [
        ("Incident Reporting", "Complaint is received through the department of Environment, Climate Change, and Forests (ENVFOR)."),
        ("Site Investigation", "Forest rangers and pollution control teams assess the area for violations and for any environmental damage."),
        ("Enforcement Action", "Offenders are fined and restoration is ordered with complainant updates."),
        ("Eco-Monitoring", "Case is closed, with long-term checks to protect forest cover and reduce pollution.")
    ],
    "Finance Department (FIN)": [
        ("Budget/Grant Filing", "Complaint is received through the finance department via online portal."),
        ("Expenditure Audit", "Finance officers review budget allocations or payment statuses to trace delays."),
        ("Fund Release", "Funds are disbursed."),
        ("Fiscal Oversight", "Complaint is closed, with analysis to optimize financial management.")
    ],
    "Handlooms, Handicrafts, Textiles, and Khadi Department (HHTK)": [
        ("Artisan Registration", "Complaint is received through the Handlooms, Handicrafts, Textiles, and Khadi Department (HHTK) via online portal."),
        ("Production Check", "Officers verify cooperative records to assess eligibility or issues."),
        ("Support Delivery", "Subsidies, looms, or market aid are provided, with updates to artisans."),
        ("Craft Promotion", "Case is closed, with efforts to boost sales tracked.")
    ],
    "Health and Family Welfare Department (HEALTH)": [
        ("Patient/Service Logging", "Complaint is received through the Health and Family Welfare Department (HEALTH) via online portal."),
        ("Facility Review", "Health inspectors check hospital stocks and staff availability to identify gaps."),
        ("Care Provision", "Medicines, treatments, and staff are deployed with updates given."),
        ("Health Outcome Check", "Complaint is closed, with monitoring to improve healthcare access.")
    ],
    "Higher Education Department (HIGHEDU)": [
        ("Student/Institution Filing", "Complaint is received through the Higher Education Department (HIGHEDU) via online portal."),
        ("Academic Audit", "Officials review college records and scholarship disbursal statuses."),
        ("Education Support", "Refunds, admissions, and grants are processed, with student notifications."),
        ("Learning Impact", "Case is closed, with data used to enhance higher education quality.")
    ],
    "Highways and Minor Ports Department (HWY)": [
        ("Road/Port Reporting", "Complaint is received through the Highways and Minor Ports Department (HWY) via online portal."),
        ("Site Survey", "Engineers inspect roads and port facilities to assess damage."),
        ("Repair Execution", "Roads are fixed and port services restored with public updates."),
        ("Infrastructure Check", "Complaint is closed, with maintenance schedules adjusted.")
    ],
    "Human Resources Management Department (PAR)": [
        ("Employee Filing", "Complaint is received through the Human Resources Management Department (PAR) via online portal."),
        ("Service Record Check", "Officers review personnel files and seniority lists for accuracy."),
        ("HR Resolution", "Promotions and transfers are processed with employee updates."),
        ("Staff Efficiency", "Case is closed, with HR policies refined.")
    ],
    "Home, Prohibition, and Excise Department (HOMEEXC)": [
        ("Incident Logging", "Complaint is received through the Home, Prohibition, and Excise Department (HOMEEXC) via online portal."),
        ("Law Enforcement Check", "Police or excise teams investigate breaches or delays in action."),
        ("Legal Action", "Offenders are penalized and safety measures enforced with updates provided."),
        ("Public Safety Review", "Complaint is closed, with crime prevention tracked.")
    ],
    "Housing and Urban Development Department (HUD)": [
        ("Housing Filing", "Complaint is received through the Housing and Urban Development Department (HUD) via online portal."),
        ("Project Audit", "Officers review housing scheme progress and land records."),
        ("Unit Allocation", "Flats or plots are allotted with complainant updates."),
        ("Urban Growth Check", "Case is closed, with urban planning improved.")
    ],
    "Industries Department (IND)": [
        ("Business Registration", "Complaint is received through the Industries Department (IND) via online portal."),
        ("Incentive Review", "Officials check industrial scheme eligibility and factory compliance."),
        ("Support Release", "Subsidies or permits are granted with business updates."),
        ("Industry Boost", "Complaint is closed, with economic growth monitored.")
    ],
    "Information Technology Department (IT)": [
        ("Tech Service Filing", "Complaint is received through the Information Technology Department (IT) via online portal."),
        ("System Check", "Tech teams troubleshoot servers and software."),
        ("Service Restoration", "Access is restored and bugs fixed with user notifications."),
        ("Digital Upgrade", "Case is closed, with IT infrastructure enhanced.")
    ],
    "Labour Welfare and Skill Development Department (LBREMP)": [
        ("Worker/Skill Logging", "Complaint is received through the Labour Welfare and Skill Development Department (LBREMP) via online portal."),
        ("Employment Audit", "Inspectors verify factory records and training program enrollment."),
        ("Welfare Delivery", "Wages, training, and benefits are provided, with worker updates."),
        ("Skill Impact", "Complaint is closed, with labour welfare tracked.")
    ],
    "Law Department (LAW)": [
        ("Legal Filing", "Complaint is received through the Law Department (LAW) via online portal."),
        ("Judicial Review", "Officers check court schedules and legal aid status."),
        ("Justice Support", "Hearings are expedited and aid provided, with updates given."),
        ("Legal Access", "Case is closed, with justice delivery improved.")
    ],
    "Legislative Assembly Department (LEGIS)": [
        ("Assembly Logging", "Complaint is received through the Legislative Assembly Department (LEGIS) via online portal."),
        ("Procedure Check", "Staff review legislative schedules and constituency issues."),
        ("Session Action", "Matters are raised and resolved in assembly with updates shared."),
        ("Governance Review", "Complaint is closed, with legislative efficiency tracked.")
    ],
    "Micro, Small, and Medium Enterprises Department (MSME)": [
        ("Enterprise Filing", "Complaint is received through the Micro, Small, and Medium Enterprises Department (MSME) via online portal."),
        ("Support Audit", "Officers verify scheme eligibility and production issues."),
        ("Aid Delivery", "Loans and machinery support are provided with business updates."),
        ("Growth Monitoring", "Complaint is closed, with MSME development assessed.")
    ],
    "Municipal Administration and Water Supply Department (MAWS)": [
        ("Civic Logging", "Complaint is received through the Municipal Administration and Water Supply Department (MAWS) via online portal."),
        ("Service Check", "Engineers inspect pipelines and garbage collection systems."),
        ("Utility Fix", "Water supply and sanitation are restored with updates."),
        ("Civic Improvement", "Complaint is closed with urban services enhanced.")
    ],
    "Public Elections Department (ELECTION)": [
        ("Voter Filing", "Complaint is received through the Public Elections Department (ELECTION) via online portal."),
        ("Roll Verification", "Officers check electoral rolls and polling station records."),
        ("Election Support", "IDs are issued and booth issues fixed, with voter updates."),
        ("Poll Integrity", "Complaint is closed, with election fairness ensured.")
    ],
    "Public Department (PUBLIC)": [
        ("Citizen Logging", "Complaint is received through the Public Department (PUBLIC) via online portal."),
        ("Admin Review", "Officers assess departmental coordination and service gaps."),
        ("Service Delivery", "Issues are resolved with updates given."),
        ("Public Trust", "Complaint is closed, with governance improved.")
    ],
    "Public Works Department (PWD)": [
        ("Project Reporting", "Complaint is received through the Public Works Department (PWD) via online portal."),
        ("Structure Check", "Engineers inspect government buildings and irrigation works."),
        ("Repair Action", "Fixes are completed with complainant updates."),
        ("Asset Maintenance", "Complaint is closed, with infrastructure upkeep tracked.")
    ],
    "Revenue and Disaster Management Department (REV)": [
        ("Land/Disaster Filing", "Complaint is received through the Revenue and Disaster Management Department (REV) via online portal."),
        ("Record Survey", "Revenue officials verify land records and disaster relief eligibility."),
        ("Relief Issuance", "Pattas and aid are provided, with updates sent."),
        ("Risk Reduction", "Complaint is closed, with disaster preparedness enhanced.")
    ],
    "Rural Development and Panchayat Raj Department (RDPR)": [
        ("Village Logging", "Complaint is received through the Rural Development and Panchayat Raj Department (RDPR) via online portal."),
        ("Worksite Check", "Officials verify rural works and scheme implementation."),
        ("Rural Support", "Wages and infrastructure are delivered, with updates."),
        ("Panchayat Progress", "Complaint is closed, with rural development tracked.")
    ],
    "School Education Department (SCHOOL)": [
        ("Student Filing", "Complaint is received through the School Education Department (SCHOOL) via online portal."),
        ("School Audit", "Officers check enrollment and supply records."),
        ("Education Delivery", "Books and uniforms are provided with updates."),
        ("Learning Check", "Complaint is closed, with education quality improved.")
    ],
    "Social Welfare and Women Empowerment Department (SWNM)": [
        ("Beneficiary Logging", "Complaint is received through the Social Welfare and Women Empowerment Department (SWNM) via online portal."),
        ("Welfare Review", "Staff verify scheme records."),
        ("Aid Provision", "Pensions and kits are disbursed with updates given."),
        ("Empowerment Tracking", "Complaint is closed, with women’s welfare assessed.")
    ],
    "Tamil Development and Information Department (TAMINF)": [
        ("Culture/Media Filing", "Complaint is received through the Tamil Development and Information Department (TAMINF) via online portal."),
        ("Content Check", "Officers review translation projects and media campaigns."),
        ("Info Delivery", "Books and broadcasts are released, with updates shared."),
        ("Cultural Reach", "Complaint is closed, with Tamil promotion tracked.")
    ],
    "Tourism, Culture, and Religious Endowments Department (TOURCUL)": [
        ("Site/Trust Logging", "Complaint is received through the Tourism, Culture, and Religious Endowments Department (TOURCUL) via online portal."),
        ("Heritage Audit", "Officials inspect tourist sites and temple accounts."),
        ("Tourism Fix", "Facilities and endowments are corrected, with updates provided."),
        ("Cultural Preservation", "Complaint is closed, with heritage protection ensured.")
    ],
    "Transport Department (TRANS)": [
        ("Vehicle/Service Filing", "Complaint is received through the Transport Department (TRANS) via online portal."),
        ("Fleet Check", "Officers review transport schedules and vehicle fitness."),
        ("Service Restoration", "Routes and permits are fixed, with commuter updates."),
        ("Mobility Review", "Complaint is closed, with transport efficiency improved.")
    ],
    "Welfare of Differently Abled Persons (DIFFABLE)": [
        ("Beneficiary Registration", "Complaint is received through the Welfare of Differently Abled Persons (DIFFABLE) via online portal."),
        ("Need Assessment", "Staff verify medical records and scheme eligibility."),
        ("Aid Delivery", "Wheelchairs and pensions are provided, with updates sent."),
        ("Inclusion Monitoring", "Complaint is closed, with accessibility tracked.")
    ],
    "Youth Welfare and Sports Development Department (YOUTHSP)": [
        ("Youth/Sport Filing", "Complaint is received through the Youth Welfare and Sports Development Department (YOUTHSP) via online portal."),
        ("Program Check", "Officers review training and competition records."),
        ("Support Release", "Funds and facilities are provided, with youth updates."),
        ("Sports Growth", "Complaint is closed, with youth engagement assessed.")
    ],
    "Water Resources Department (WRD)": [
        ("Waterway Logging", "Complaint is received through the Water Resources Department (WRD) via online portal."),
        ("System Survey", "Engineers inspect dams, canals, and tanks for issues."),
        ("Water Fix", "Repairs and water releases are executed with farmer updates."),
        ("Resource Management", "Complaint is closed, with water security improved.")
    ],
    "Planning, Development, and Special Initiatives Department (PLGDEV)": [
        ("Project Filing", "Complaint is received through the Planning, Development, and Special Initiatives Department (PLGDEV) via online portal."),
        ("Plan Review", "Officers assess development project timelines and funding."),
        ("Initiative Rollout", "Projects are expedited with stakeholder updates."),
        ("Development Tracking", "Complaint is closed, with progress monitored.")
    ],
    "Special Programme Implementation (SPI)": [
        ("Programme Registration", "Complaint is received through the Planning, Development, and Special Initiatives Department (PLGDEV) via online portal."),
        ("Implementation Review", "Officers assess project timelines, funding status, and coordination issues by cross-checking records with implementing agencies."),
        ("Scheme Execution", "Resolutions like expediting vehicle delivery, releasing funds, or clearing bottlenecks are implemented with updates."),
        ("Progress Oversight", "Complaint is closed, with progress monitored.")
    ]
}

# Helper functions for keyword processing
def get_wordnet_pos(word):
    tag = nltk.pos_tag([word])[0][1][0].upper()
    tag_dict = {"J": wn.ADJ, "N": wn.NOUN, "V": wn.VERB, "R": wn.ADV}
    return tag_dict.get(tag, wn.NOUN)

def get_synonyms(word):
    synonyms = set()
    for syn in wn.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemmatizer.lemmatize(lemma.name()))
    return synonyms

# Initialize keyword_sets
keyword_sets = {}
for dept, base_keywords in [
    ("Adi Dravidar and Tribal Welfare Department (ADW)", adw_base),
    ("Agriculture and Farmers Welfare Department (AGRI)", agri_base),
    ("Animal Husbandry and Dairying and Fisheries and Fishermen Welfare Department (AHFISH)", ahfish_base),
    ("BC MBC and Minorities Welfare Department (BCMBC)", bcmbc_base),
    ("Co-operation Food and Consumer Protection Department (FOODCO)", foodco_base),
    ("Commercial Taxes and Registration Department (CTREG)", ctreg_base),
    ("Energy Department (ENERGY)", energy_base),
    ("Environment Climate Change and Forests Department (ENVFOR)", envfor_base),
    ("Finance Department (FIN)", fin_base),
    ("Handlooms Handicrafts Textiles and Khadi Department (HHTK)", hhtk_base),
    ("Health and Family Welfare Department (HEALTH)", health_base),
    ("Higher Education Department (HIGHEDU)", highedu_base),
    ("Highways and Minor Ports Department (HWY)", hwy_base),
    ("Human Resources Management Department (PAR)", par_base),
    ("Home Prohibition and Excise Department (HOMEEXC)", homeexc_base),
    ("Housing and Urban Development Department (HUD)", hud_base),
    ("Industries Department (IND)", ind_base),
    ("Information Technology Department (IT)", it_base),
    ("Labour Welfare and Skill Development Department (LBREMP)", lbremp_base),
    ("Law Department (LAW)", law_base),
    ("Legislative Assembly Department (LEGIS)", legis_base),
    ("Micro Small and Medium Enterprises Department (MSME)", msme_base),
    ("Municipal Administration and Water Supply Department (MAWS)", maws_base),
    ("Public Elections Department (ELECTION)", election_base),
    ("Public Department (PUBLIC)", public_base),
    ("Public Works Department (PWD)", pwd_base),
    ("Revenue and Disaster Management Department (REV)", rev_base),
    ("Rural Development and Panchayat Raj Department (RDPR)", rdpr_base),
    ("School Education Department (SCHOOL)", school_base),
    ("Social Welfare and Women Empowerment Department (SWNM)", swnm_base),
    ("Tamil Dev. and Information Department (TAMINF)", taminf_base),
    ("Tourism Culture and Religious Endowments Department (TOURCUL)", tourcul_base),
    ("Transport Department (TRANS)", trans_base),
    ("Welfare of Differently Abled Persons (DIFFABLE)", diffable_base),
    ("Youth Welfare and Sports Development Department (YOUTHSP)", youthsp_base),
    ("Water Resources Department (WRD)", wrd_base),
    ("Planning Development Department (PLGDEV)", plgdev_base),
    ("Special Programme Implementation (SPI)", spi_base)
]:
    keyword_set = set()
    for word in base_keywords:
        keyword_set.add(lemmatizer.lemmatize(word))
        keyword_set.update(get_synonyms(word))
    keyword_sets[dept] = keyword_set

# Database connection
def get_db_connection():
    try:
        conn = pymysql.connect(**db_config)
        return conn
    except pymysql.Error as e:
        st.error(f"Failed to connect to MySQL: {e}")
        return None

# Validation functions
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_mobile(mobile):
    pattern = r'^\d{10}$'
    return re.match(pattern, mobile) is not None

# Database table creation
def create_log_details_table():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_details (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                mobile VARCHAR(10) NOT NULL,
                email VARCHAR(100) NOT NULL,
                address TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

def create_complaints_table():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                petition_code VARCHAR(10) UNIQUE NOT NULL,
                user_id VARCHAR(50) NOT NULL,
                filename VARCHAR(255) NOT NULL,
                department VARCHAR(255),
                upload_time TIMESTAMP,
                incharge VARCHAR(100),
                priority VARCHAR(50),
                sentiment_score FLOAT,
                progress INT DEFAULT 1
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

def create_chat_messages_table():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                petition_code VARCHAR(10) NOT NULL,
                sender VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (petition_code) REFERENCES complaints(petition_code)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

def migrate_database():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        # Existing migrations
        cursor.execute("SHOW COLUMNS FROM complaints LIKE 'petition_code'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE complaints ADD COLUMN petition_code VARCHAR(10) UNIQUE NOT NULL DEFAULT ''")
            cursor.execute("UPDATE complaints SET petition_code = CONCAT('PE-', LPAD(id, 4, '0')) WHERE petition_code = ''")
        cursor.execute("SHOW COLUMNS FROM complaints LIKE 'progress'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE complaints ADD COLUMN progress INT DEFAULT 1")
        cursor.execute("SHOW COLUMNS FROM complaints LIKE 'sentiment_score'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE complaints ADD COLUMN sentiment_score FLOAT")
        
        # New migration to handle NULL sentiment_score
        cursor.execute("UPDATE complaints SET sentiment_score = 0 WHERE sentiment_score IS NULL")
        cursor.execute("ALTER TABLE complaints MODIFY COLUMN sentiment_score FLOAT NOT NULL DEFAULT 0")
        
        conn.commit()
        cursor.close()
        conn.close()

# Check for repeated petitions
def check_repeated_petition(category, user_id, extracted_keywords, town):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT petition_code, progress, user_id, filename, sentiment_score 
            FROM complaints 
            WHERE department = %s AND user_id != %s
        """, (category, user_id))
        existing_complaints = cursor.fetchall()

        is_duplicate = False
        duplicate_details = None
        for petition_code, progress, existing_user_id, existing_filename, sentiment_score in existing_complaints:
            existing_text = ""
            if os.path.exists(existing_filename):
                with open(existing_filename, 'rb') as f:
                    existing_text = extract_text_from_pdf(f)
            else:
                st.warning(f"Existing file {existing_filename} not found on server. Skipping file-based check.")
            existing_keywords = extract_keywords(existing_text) if existing_text else []
            if town in existing_keywords and sentiment_score < -0.3:
                is_duplicate = True
                duplicate_details = (petition_code, existing_user_id)
                break
        cursor.close()
        conn.close()
    return is_duplicate, duplicate_details[0] if duplicate_details else None, duplicate_details[1] if duplicate_details else None

# User registration
def register_user(name, username, password, mobile, email, address):
    if not all([name, username, password, mobile, email, address]):
        st.error("All fields are required.")
        return False
    if not is_valid_email(email):
        st.error("Invalid email format.")
        return False
    if not is_valid_mobile(mobile):
        st.error("Mobile number must be 10 digits.")
        return False

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT username FROM log_details WHERE username = %s", (username,))
            if cursor.fetchone():
                st.error("Username already exists. Please choose a different username.")
                return False
            cursor.execute("""
                INSERT INTO log_details (name, username, password, mobile, email, address)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, username, password, mobile, email, address))
            conn.commit()
            st.success("Registration successful! Please sign in.")
            return True
        except Exception as e:
            st.error(f"Registration failed: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False

# User authentication
def authenticate_user(username, password):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, name, mobile, email, address FROM log_details WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            st.session_state.logged_in_user = user[0]
            st.session_state.user_details = {
                "name": user[1],
                "mobile": user[2],
                "email": user[3],
                "address": user[4]
            }
            return True
    return False

# Count user complaints
def get_user_complaint_count(username):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE user_id = %s", (username,))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    return 0

# Town names
town_names = ["munnur", "chennai", "coimbatore", "madurai", "tiruchirappalli", "salem", "erode", "tirunelveli", "vellore", "thanjavur"]

# Extract keywords
def extract_keywords(text):
    text = text.lower()
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    keywords = [lemmatizer.lemmatize(word, get_wordnet_pos(word)) 
                for word in tokens if word.isalpha() and word not in stop_words]
    
    for town in town_names:
        if town in text.lower():
            keywords.append(town)
    return keywords

# Categorize PDF with sentiment analysis
def categorize_pdf(text, filename):
    extracted_keywords = extract_keywords(text)
    keyword_freq = Counter(extracted_keywords)
    
    # Sentiment Analysis
    sentiment_scores = sid.polarity_scores(text)
    sentiment_score = sentiment_scores['compound']
    
    # Categorization
    scores = {dept: len(set(extracted_keywords) & keyword_sets[dept]) for dept in keyword_sets.keys()}
    max_score = max(scores.values())
    if max_score > 0:
        category = max(scores, key=scores.get)
    else:
        category = None

    return category, keyword_freq, extracted_keywords, sentiment_score

# Categorize page
def categorize_page():
    st.title("Complaints Categorization & Prioritization")
    st.write("Upload Complaint files to categorize them into departments and prioritize based on sentiment and content.")

    user_id = st.session_state.logged_in_user
    st.write(f"Submitting petition as: **{user_id}**")

    uploaded_files = st.file_uploader("Choose Complaint files", type="pdf", accept_multiple_files=True)

    conn = get_db_connection()
    if conn is None:
        st.error("Failed to establish database connection.")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT filename, petition_code, department, progress FROM complaints")
        existing_complaints = {row[0]: {"petition_code": row[1], "department": row[2], "progress": row[3]} for row in cursor.fetchall()}

        if uploaded_files:
            st.write("Processing uploaded files...")
            processed_files = set()

            for uploaded_file in uploaded_files:
                if uploaded_file.name in existing_complaints:
                    petition_code = existing_complaints[uploaded_file.name]["petition_code"]
                    department = existing_complaints[uploaded_file.name]["department"]
                    progress = existing_complaints[uploaded_file.name]["progress"]
                    if department in progress_steps:
                        steps = progress_steps[department]
                        progress_percentage = progress / len(steps)
                        st.info(f"File {uploaded_file.name} already submitted. Petition Code: **{petition_code}**")
                        st.write(f"**Petition Progress:** {progress_percentage * 100:.0f}%")
                        st.progress(progress_percentage)
                        st.write(f"**Current Step:** {steps[progress-1][0]}")
                        st.write(f"**Details:** {steps[progress-1][1]}")
                    else:
                        st.warning(f"Skipping {uploaded_file.name} as it has already been submitted. Petition Code: **{petition_code}**")
                    continue

                pdf_text = extract_text_from_pdf(uploaded_file)
                st.subheader(f"Results for: {uploaded_file.name}")
                st.write("*Extracted Text:*")
                st.text_area("Text", pdf_text, height=200, key=f"text_area_{uploaded_file.name}")

                extracted_keywords = extract_keywords(pdf_text)
                st.write("*Extracted Lemmatized Keywords:*", ", ".join(extracted_keywords[:10]))
       
                category, keyword_freq, extracted_keywords, sentiment_score = categorize_pdf(pdf_text, uploaded_file.name)
                if category:
                    top_complaints = set([kw for kw, _ in Counter(extracted_keywords).most_common(10)])
                    doc_priority_score = sum(keyword_freq[kw] for kw in extracted_keywords if kw in top_complaints)
                    priority = assign_priority(doc_priority_score, sentiment_score)
                    st.success(f"Categorized as: *{category}* ({priority} Priority, Sentiment Score: {sentiment_score:.2f})")

                    upload_time = datetime.now()
                    incharge = department_incharge.get(category, {"name": "Not Assigned", "id": "UNKNOWN"})["name"]

                    cursor.execute("SELECT MAX(id) FROM complaints")
                    max_id = cursor.fetchone()[0] or 0
                    petition_code = f"PE-{max_id + 1:04d}"

                    cursor.execute("""
                        INSERT INTO complaints (petition_code, user_id, filename, department, upload_time, incharge, priority, sentiment_score, progress)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (petition_code, user_id, uploaded_file.name, category, upload_time, incharge, priority, sentiment_score, 1))
                    conn.commit()
                    st.info(f"Your petition has been submitted successfully! Your petition code is: **{petition_code}**.")
                else:
                    st.warning("Could not categorize - no matching keywords found")
                    # Assign a default sentiment_score and log the complaint
                    sentiment_score = 0
                    cursor.execute("SELECT MAX(id) FROM complaints")
                    max_id = cursor.fetchone()[0] or 0
                    petition_code = f"PE-{max_id + 1:04d}"
                    cursor.execute("""
                        INSERT INTO complaints (petition_code, user_id, filename, department, upload_time, incharge, priority, sentiment_score, progress)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (petition_code, user_id, uploaded_file.name, "Uncategorized", upload_time, "Not Assigned", "Low", sentiment_score, 1))
                    conn.commit()
                    st.info(f"Your petition has been logged as Uncategorized. Petition code: **{petition_code}**.")
            
                processed_files.add(uploaded_file.name)

            st.session_state.selected_file = {"data": None, "name": None}
            display_priorities()

        if not uploaded_files and not st.session_state.selected_file["data"]:
            st.info("Please upload Complaint files to begin.")

    finally:
        if conn.open:
            conn.close()  # Close only if still open
        st.session_state.selected_file = {"data": None, "name": None}
        
# Extract text from PDF
def extract_text_from_pdf(pdf_file):
    try:
        text = ""
        if isinstance(pdf_file, str):
            with open(pdf_file, 'rb') as f:
                with pdfplumber.open(f) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
        else:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Failed to extract text from {pdf_file}: {e}")
        return ""

# Assign priority based on keyword score and sentiment
def assign_priority(keyword_score, sentiment_score):
    normalized_keyword = min(keyword_score / 20, 1.0)
    sentiment_weight = (-sentiment_score + 1) / 2
    combined_score = 0.6 * sentiment_weight + 0.4 * normalized_keyword
    
    if combined_score >= 0.7:
        return "High"
    elif 0.4 <= combined_score < 0.7:
        return "Medium"
    else:
        return "Low"

priority_values = {"High": 3, "Medium": 2, "Low": 1}

# Get highest priority for a department
def get_highest_priority(dept):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT priority FROM complaints WHERE department = %s", (dept,))
        priorities = cursor.fetchall()
        cursor.close()
        conn.close()
        if priorities:
            priority_nums = [priority_values.get(priority[0], 0) for priority in priorities]
            return max(priority_nums)
    return 0

# Get minimum sentiment score for a department
def get_min_sentiment(dept):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sentiment_score FROM complaints WHERE department = %s", (dept,))
        sentiments = cursor.fetchall()
        cursor.close()
        conn.close()
        valid_sentiments = [sent[0] for sent in sentiments if sent[0] is not None]
        return min(valid_sentiments) if valid_sentiments else 0
    return 0

# Fetch complaints for a department
def fetch_complaints_for_department(dept):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT filename, priority, sentiment_score FROM complaints WHERE department = %s", (dept,))
        complaints = cursor.fetchall()
        cursor.close()
        conn.close()
        return complaints
    return []

# Display priorities
def display_priorities():
    st.subheader("Prioritized Complaints by Department")
    
    sorted_depts = sorted(
        keyword_sets.keys(),
        key=lambda dept: (-get_highest_priority(dept), get_min_sentiment(dept), dept)
    )
    
    for dept in sorted_depts:
        with st.expander(dept, expanded=False):
            complaints = fetch_complaints_for_department(dept)
            if complaints:
                st.write("*Complaints Priorities:*")
                sorted_complaints = sorted(
                    complaints,
                    key=lambda x: priority_values.get(x[1], 0),
                    reverse=True
                )
                for filename, priority, sentiment_score in sorted_complaints:
                    st.write(f"- {filename} ({priority} Priority, Sentiment: {sentiment_score:.2f})")
            else:
                st.write("No Complaints recorded yet.")

# Navigation bar
def navigation_bar():
    st.markdown("---")
    if st.session_state.page == "officials" and st.session_state.official_id:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button(f"👤 Official", key="official_profile"):
                st.session_state.page = "officials"
                st.rerun()
        with col2:
            if st.button("Logout", key="nav_logout"):
                st.session_state.logged_in_user = None
                st.session_state.user_details = {}
                st.session_state.official_id = None
                st.session_state.page = "login"
                st.session_state.show_profile = False
                st.session_state.selected_file = {"data": None, "name": None}
                st.session_state.profile_user_id = None
                st.session_state.update_petition_code = None
                st.session_state.chat_history = {}
                st.rerun()
    else:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Home", key="nav_home"):
                st.session_state.page = "home"
                st.rerun()
        with col2:
            if st.session_state.logged_in_user or st.session_state.official_id:
                user_name = st.session_state.user_details.get("name", "User") if st.session_state.logged_in_user else "Official"
                if st.button(f"👤 {user_name}", key="user_profile"):
                    st.session_state.profile_user_id = st.session_state.logged_in_user
                    st.session_state.page = "profile" if st.session_state.logged_in_user else "officials"
                    st.rerun()
        with col3:
            if st.session_state.logged_in_user or st.session_state.official_id:
                if st.button("Logout", key="nav_logout"):
                    st.session_state.logged_in_user = None
                    st.session_state.user_details = {}
                    st.session_state.official_id = None
                    st.session_state.page = "login"
                    st.session_state.show_profile = False
                    st.session_state.selected_file = {"data": None, "name": None}
                    st.session_state.profile_user_id = None
                    st.session_state.update_petition_code = None
                    st.session_state.chat_history = {}
                    st.rerun()
    st.markdown("---")

# Profile page
def profile_page():
    st.title("User Profile")
    if st.session_state.logged_in_user and "user_details" in st.session_state:
        user_name = st.session_state.user_details["name"]
        st.write(f"**User ID:** {st.session_state.logged_in_user}")
        st.write(f"**Name:** {user_name}")
        st.write(f"**Mobile Number:** {st.session_state.user_details['mobile']}")
        st.write(f"**Email:** {st.session_state.user_details['email']}")
        st.write(f"**Address:** {st.session_state.user_details['address']}")
        complaint_count = get_user_complaint_count(st.session_state.logged_in_user)
        st.write(f"**Number of Complaints Submitted:** {complaint_count}")

        st.subheader("Your Submitted Petitions")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT petition_code, filename, department, progress FROM complaints WHERE user_id = %s", 
                           (st.session_state.logged_in_user,))
            petitions = cursor.fetchall()
            cursor.close()
            conn.close()

            if petitions:
                for petition in petitions:
                    petition_code, filename, department, progress = petition
                    st.write(f"- **Petition Code:** {petition_code} | **Complaint Name:** {filename}")
                    if department in progress_steps:
                        steps = progress_steps[department]
                        st.write("**Petition Progress:**")
                        progress_percentage = progress / len(steps)
                        display_percentage = progress_percentage * 100
                        st.write(f"Progress: {display_percentage:.0f}%")
                        st.progress(progress_percentage)
                        st.write(f"**Current Step:** {steps[progress-1][0]}")
                        st.write(f"**Details:** {steps[progress-1][1]}")
                    else:
                        st.write("**Petition Progress:** Not available for this department.")

                    # Chat with Official
                    st.subheader("Chat with Official")
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT sender, message, timestamp FROM chat_messages WHERE petition_code = %s ORDER BY timestamp ASC",
                                       (petition_code,))
                        messages = cursor.fetchall()
                        cursor.close()
                        conn.close()

                        if petition_code not in st.session_state.chat_history:
                            st.session_state.chat_history[petition_code] = []

                        if messages:
                            for message in messages:
                                sender, msg_text, timestamp = message
                                st.session_state.chat_history[petition_code].append({"sender": sender, "message": msg_text, "timestamp": timestamp})
                                st.write(f"**{sender} ({timestamp}):** {msg_text}")
                        else:
                            st.write("No messages yet. Start the conversation!")

                        message = st.text_input("Your message:", key=f"user_message_{petition_code}")
                        if st.button("Send", key=f"send_user_{petition_code}"):
                            if message:
                                conn = get_db_connection()
                                if conn:
                                    cursor = conn.cursor()
                                    cursor.execute("INSERT INTO chat_messages (petition_code, sender, message) VALUES (%s, %s, %s)",
                                                   (petition_code, st.session_state.logged_in_user, message))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                                    st.success("Message sent!")
                                    st.rerun()

                    st.markdown("---")
            else:
                st.write("No petitions submitted yet.")
        
        if st.button("Back to Home"):
            st.session_state.page = "home"
            st.rerun()

# Login page
def login_page():
    st.title("ResolveAI")
    st.write("Streamline grievance resolution with AI-powered tools.")

    st.markdown("### Login Options")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("User Login")
        if st.button("User Sign In"):
            st.session_state.page = "sign_in"
            st.rerun()
        if st.button("User Sign Up"):
            st.session_state.page = "sign_up"
            st.rerun()
    with col2:
        st.subheader("Official Login")
        if st.button("Official Sign In"):
            st.session_state.page = "official_sign_in"
            st.rerun()

# Sign-up page
def sign_up_page():
    st.title("User Sign Up")
    name = st.text_input("Name")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    mobile = st.text_input("Mobile Number (10 digits)")
    email = st.text_input("Email ID")
    address = st.text_area("Address")

    if st.button("Register"):
        if register_user(name, username, password, mobile, email, address):
            st.session_state.page = "login"
            st.rerun()

# Sign-in page
def sign_in_page():
    st.title("User Sign In")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if authenticate_user(username, password):
            st.session_state.page = "home"
            st.session_state.show_profile = False
            st.rerun()
        else:
            st.error("No user found. Try signing up.")

# Official sign-in page
def official_sign_in_page():
    st.title("Official Sign In")
    official_id = st.text_input("Enter your Official ID:", help="Enter the ID assigned to you as a department head.")
    
    if st.button("Login"):
        official_dept = None
        official_name = None
        for dept, info in department_incharge.items():
            if info["id"] == official_id:
                official_dept = dept
                official_name = info["name"]
                break

        if official_dept:
            st.session_state.official_id = official_id
            st.session_state.page = "officials"
            st.rerun()
        else:
            st.error("Invalid Official ID. Please check your ID and try again.")

# Home page
def home_page():
    st.title("ResolveAI")
    st.write("Streamline grievance resolution with AI-powered tools.")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Submit a Petition", key="submit_petition"):
            st.session_state.page = "categorize"
            st.rerun()
    with col2:
        if st.button("Track Your Petition", key="track_petition"):
            st.session_state.page = "track"
            st.rerun()
    
    st.markdown("---")
    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown("**Categorization & Classification**")
        st.write("AI-driven petition sorting.")
    with col5:
        st.markdown("**Real-Time Updates**")
        st.write("Transparency at every step.")
    with col6:
        st.markdown("**Automation**")
        st.write("Automated reminders and task scheduling.")

# Track page
def track_page():
    st.title("Track Your Petition")
    st.write("Enter your Petition Code to track the status of your petition.")

    petition_code = st.text_input("Enter your Petition Code (e.g., PE-0001):", help="Enter the Petition Code provided when you submitted your petition.")
    if petition_code:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, filename, department, upload_time, incharge, priority, progress, sentiment_score FROM complaints WHERE petition_code = %s", 
                           (petition_code,))
            complaints = cursor.fetchall()
            cursor.close()
            conn.close()

            if complaints:
                st.success(f"Found {len(complaints)} petition(s)!")
                for idx, complaint in enumerate(complaints, 1):
                    user_id, filename, department, upload_time, incharge, priority, progress, sentiment_score = complaint
                    st.write(f"**Petition {idx} Details:**")
                    st.write(f"- **User ID:** {user_id}")
                    st.write(f"- **Filename:** {filename}")
                    st.write(f"- **Department:** {department}")
                    st.write(f"- **Upload Date and Time:** {upload_time}")
                    st.write(f"- **In Charge:** {incharge}")
                    st.write(f"- **Priority:** {priority}")
                    st.write(f"- **Sentiment Score:** {sentiment_score:.2f}")
                    if department in progress_steps:
                        steps = progress_steps[department]
                        st.write("**Petition Progress:**")
                        progress_percentage = progress / len(steps)
                        display_percentage = progress_percentage * 100
                        st.write(f"Progress: {display_percentage:.0f}%")
                        st.progress(progress_percentage)
                        st.write(f"**Current Step:** {steps[progress-1][0]}")
                        st.write(f"**Details:** {steps[progress-1][1]}")
                    else:
                        st.write("**Petition Progress:** Not available for this department.")

                    # Chat with Official
                    st.subheader("Chat with Official")
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT sender, message, timestamp FROM chat_messages WHERE petition_code = %s ORDER BY timestamp ASC",
                                       (petition_code,))
                        messages = cursor.fetchall()
                        cursor.close()
                        conn.close()

                        if petition_code not in st.session_state.chat_history:
                            st.session_state.chat_history[petition_code] = []

                        if messages:
                            for message in messages:
                                sender, msg_text, timestamp = message
                                st.session_state.chat_history[petition_code].append({"sender": sender, "message": msg_text, "timestamp": timestamp})
                                st.write(f"**{sender} ({timestamp}):** {msg_text}")
                        else:
                            st.write("No messages yet. Start the conversation!")

                        if st.session_state.logged_in_user == user_id:
                            message = st.text_input("Your message:", key=f"user_message_{petition_code}")
                            if st.button("Send", key=f"send_user_{petition_code}"):
                                if message:
                                    conn = get_db_connection()
                                    if conn:
                                        cursor = conn.cursor()
                                        cursor.execute("INSERT INTO chat_messages (petition_code, sender, message) VALUES (%s, %s, %s)",
                                                       (petition_code, user_id, message))
                                        conn.commit()
                                        cursor.close()
                                        conn.close()
                                        st.success("Message sent!")
                                        st.rerun()

                    st.markdown("---")
            else:
                st.error("Invalid or unknown Petition Code. Please check the code and try again.")

# Send email
def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = to_email

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# Get user email
def get_user_email(user_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM log_details WHERE username = %s", (user_id,))
        email = cursor.fetchone()
        cursor.close()
        conn.close()
        return email[0] if email else None
    return None

# Update progress page
def update_progress_page():
    st.title("Update Petition Progress")
    petition_code = st.session_state.get("update_petition_code", None)
    if not petition_code:
        st.error("No petition selected for update.")
        return

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT department, progress, user_id FROM complaints WHERE petition_code = %s", (petition_code,))
        complaint = cursor.fetchone()
        if complaint:
            department, current_progress, user_id = complaint
            if department in progress_steps:
                steps = progress_steps[department]
                st.write(f"**Petition Code:** {petition_code}")
                st.write(f"**Department:** {department}")
                st.write("**Current Progress:**")
                progress_percentage = current_progress / len(steps)
                display_percentage = progress_percentage * 100
                st.write(f"Progress: {display_percentage:.0f}%")
                st.progress(progress_percentage)
                st.write(f"**Current Step:** {steps[current_progress-1][0]}")
                st.write(f"**Details:** {steps[current_progress-1][1]}")

                st.subheader("Update Progress")
                new_step = st.selectbox("Select the current step:", 
                                      options=[(i+1, step[0]) for i, step in enumerate(steps)],
                                      format_func=lambda x: x[1],
                                      index=current_progress-1)
                if st.button("Update"):
                    cursor.execute("UPDATE complaints SET progress = %s WHERE petition_code = %s", (new_step[0], petition_code))
                    conn.commit()

                    cursor.execute("SELECT progress FROM complaints WHERE petition_code = %s", (petition_code,))
                    updated_progress = cursor.fetchone()[0]
                    updated_progress_percentage = updated_progress / len(steps)
                    updated_display_percentage = updated_progress_percentage * 100

                    user_email = get_user_email(user_id)
                    if user_email:
                        subject = f"Update on Petition {petition_code}"
                        body = f"""
                        Dear User,

                        The status of your petition (Petition Code: {petition_code}) has been updated.

                        **New Progress:** {updated_display_percentage:.0f}%
                        **Current Step:** {steps[updated_progress-1][0]}
                        **Details:** {steps[updated_progress-1][1]}

                        Thank you for your patience.

                        Regards,
                        ResolveAI Team
                        """
                        if send_email(user_email, subject, body):
                            st.success("Progress updated and email sent successfully!")
                        else:
                            st.success("Progress updated, but email failed to send.")
                    else:
                        st.success("Progress updated, but user email not found.")

                    st.session_state.page = "officials"
                    st.rerun()
            else:
                st.error("Progress steps not defined for this department.")
        else:
            st.error("Petition not found.")
        cursor.close()
        conn.close()

    if st.button("Back to Officials Page"):
        st.session_state.page = "officials"
        st.rerun()

# Officials page
def officials_page():
    navigation_bar()
    st.title("For Officials")
    official_id = st.session_state.get("official_id", "")
    
    official_dept = None
    official_name = None
    for dept, info in department_incharge.items():
        if info["id"] == official_id:
            official_dept = dept
            official_name = info["name"]
            break

    if official_dept:
        st.success(f"Welcome, {official_name}! You are the head of {official_dept}")
        st.write("### Assigned Complaints")

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT petition_code, user_id, filename, upload_time, priority, progress, sentiment_score 
                FROM complaints 
                WHERE department = %s
            """, (official_dept,))
            assigned_complaints = cursor.fetchall()
            cursor.close()
            conn.close()

            if assigned_complaints:
                resolution_deadlines = {"High": 7, "Medium": 14, "Low": 30}
                for complaint in assigned_complaints:
                    petition_code, user_id, filename, upload_time, priority, progress, sentiment_score = complaint
                    with st.expander(f"Complaint by User ID: {user_id} (Petition Code: {petition_code})"):
                        st.write(f"- **Petition Code:** {petition_code}")
                        st.write(f"- **Filename:** {filename}")
                        st.write(f"- **Department:** {official_dept}")
                        st.write(f"- **Upload Date and Time:** {upload_time}")
                        st.write(f"- **Priority:** {priority}")
                        st.write(f"- **Sentiment Score:** {sentiment_score:.2f}")

                        if official_dept in progress_steps:
                            steps = progress_steps[official_dept]
                            st.write("**Petition Progress:**")
                            progress_percentage = progress / len(steps)
                            display_percentage = progress_percentage * 100
                            st.write(f"Progress: {display_percentage:.0f}%")
                            st.progress(progress_percentage)
                            st.write(f"**Current Step:** {steps[progress-1][0]}")
                            st.write(f"**Details:** {steps[progress-1][1]}")

                        deadline = upload_time + timedelta(days=resolution_deadlines[priority])
                        time_remaining = deadline - datetime.now()
                        if time_remaining.total_seconds() > 0:
                            days_remaining = time_remaining.days
                            hours_remaining = time_remaining.seconds // 3600
                            minutes_remaining = (time_remaining.seconds % 3600) // 60
                            st.write(f"- **Time Remaining:** {days_remaining} days, {hours_remaining} hours, {minutes_remaining} minutes")
                        else:
                            st.write(f"- **Time Remaining:** Overdue by {-time_remaining.days} days")

                        # Chat with User
                        st.subheader("Chat with User")
                        conn = get_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT sender, message, timestamp FROM chat_messages WHERE petition_code = %s ORDER BY timestamp ASC",
                                           (petition_code,))
                            messages = cursor.fetchall()
                            cursor.close()
                            conn.close()

                            if petition_code not in st.session_state.chat_history:
                                st.session_state.chat_history[petition_code] = []

                            if messages:
                                for message in messages:
                                    sender, msg_text, timestamp = message
                                    st.session_state.chat_history[petition_code].append({"sender": sender, "message": msg_text, "timestamp": timestamp})
                                    st.write(f"**{sender} ({timestamp}):** {msg_text}")
                            else:
                                st.write("No messages yet. Start the conversation!")

                            message = st.text_input("Your message:", key=f"official_message_{petition_code}")
                            if st.button("Send", key=f"send_official_{petition_code}"):
                                if message:
                                    conn = get_db_connection()
                                    if conn:
                                        cursor = conn.cursor()
                                        cursor.execute("INSERT INTO chat_messages (petition_code, sender, message) VALUES (%s, %s, %s)",
                                                       (petition_code, official_id, message))
                                        conn.commit()
                                        cursor.close()
                                        conn.close()
                                        st.success("Message sent!")
                                        st.rerun()

                        col1, col2 = st.columns(2)
                        with col1:
                            st.button("Download Petition", key=f"download_{petition_code}", disabled=True)
                        with col2:
                            if st.button("Update", key=f"update_{petition_code}"):
                                st.session_state.update_petition_code = petition_code
                                st.session_state.page = "update_progress"
                                st.rerun()
            else:
                st.info("No complaints assigned to your department at this time.")
    else:
        st.error("Invalid Official ID. Please try logging in again.")

# Main function
def main():
    create_log_details_table()
    create_complaints_table()
    create_chat_messages_table()
    migrate_database()

    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "logged_in_user" not in st.session_state:
        st.session_state.logged_in_user = None
    if "user_details" not in st.session_state:
        st.session_state.user_details = {}
    if "official_id" not in st.session_state:
        st.session_state.official_id = None
    if "show_profile" not in st.session_state:
        st.session_state.show_profile = False
    if "selected_file" not in st.session_state:
        st.session_state.selected_file = {"data": None, "name": None}
    if "profile_user_id" not in st.session_state:
        st.session_state.profile_user_id = None
    if "update_petition_code" not in st.session_state:
        st.session_state.update_petition_code = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}

    if st.session_state.page == "login":
        login_page()
    elif st.session_state.page == "sign_in":
        sign_in_page()
    elif st.session_state.page == "sign_up":
        sign_up_page()
    elif st.session_state.page == "official_sign_in":
        official_sign_in_page()
    elif st.session_state.page == "officials":
        officials_page()
    elif st.session_state.page == "update_progress":
        update_progress_page()
    else:
        if st.session_state.logged_in_user:
            navigation_bar()
            if st.session_state.page == "home":
                home_page()
            elif st.session_state.page == "categorize":
                categorize_page()
            elif st.session_state.page == "track":
                track_page()
            elif st.session_state.page == "profile":
                profile_page()

if __name__ == "__main__":
    main()