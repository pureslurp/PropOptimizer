"""
Check The Odds API usage limits and remaining requests
"""

import requests
from config import ODDS_API_KEY


def check_api_usage():
    """Check API usage limits from The Odds API"""
    
    if ODDS_API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Error: API key not configured!")
        print("Please set ODDS_API_KEY in your environment or Streamlit secrets")
        return
    
    # Make a simple request to check usage (using sports endpoint as it's lightweight)
    url = "https://api.the-odds-api.com/v4/sports"
    params = {
        'apiKey': ODDS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        # Print status
        print("=" * 60)
        print("THE ODDS API - USAGE CHECK")
        print("=" * 60)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API Key is valid and working")
        else:
            print(f"⚠️  Warning: Received status code {response.status_code}")
        
        # Check for usage headers
        print("\n" + "-" * 60)
        print("USAGE STATISTICS")
        print("-" * 60)
        
        headers = response.headers
        
        # The Odds API provides these headers
        requests_used = headers.get('x-requests-used', 'N/A')
        requests_remaining = headers.get('x-requests-remaining', 'N/A')
        requests_last = headers.get('x-requests-last', 'N/A')
        
        print(f"Requests Used:      {requests_used}")
        print(f"Requests Remaining: {requests_remaining}")
        print(f"Last Request Time:  {requests_last}")
        
        # Calculate percentage if we have the data
        if requests_used != 'N/A' and requests_remaining != 'N/A':
            try:
                used = int(requests_used)
                remaining = int(requests_remaining)
                total = used + remaining
                percentage_used = (used / total) * 100 if total > 0 else 0
                
                print(f"\nTotal Quota:        {total} requests")
                print(f"Percentage Used:    {percentage_used:.1f}%")
                
                # Warning if running low
                if percentage_used > 80:
                    print("\n⚠️  WARNING: You've used over 80% of your quota!")
                elif percentage_used > 50:
                    print("\n⚡ NOTICE: You've used over 50% of your quota")
                else:
                    print("\n✅ You have plenty of requests remaining")
                    
            except ValueError:
                pass
        
        # Print all headers for debugging
        print("\n" + "-" * 60)
        print("ALL RESPONSE HEADERS")
        print("-" * 60)
        for key, value in headers.items():
            print(f"{key}: {value}")
        
        print("\n" + "=" * 60)
        
        # Information about typical limits
        print("\nTYPICAL API LIMITS:")
        print("  - Free tier: 500 requests/month")
        print("  - Starter tier: 10,000 requests/month")
        print("  - Pro tier: 50,000+ requests/month")
        print("\nEach main data fetch uses multiple requests:")
        print("  - 1 request for events list")
        print("  - 1 request per game for main player props (up to 5 games)")
        print("  - 1 request per game per stat type for alternate lines")
        print("  - Total per refresh: ~6-40+ requests depending on stat types")
        print("\n" + "=" * 60)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error making API request: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    check_api_usage()

