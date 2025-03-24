import sys
import logging

# 重新配置 stdout，避免乱码
sys.stdout.reconfigure(encoding='utf-8')

# 配置日志
handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[handler]
)
logger = logging.getLogger("HKJC_Scraper")