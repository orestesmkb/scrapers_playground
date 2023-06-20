import numpy as np
import pandas as pd

# Non existing values must be null and not zero in the data frames

from pymongo import MongoClient


def is_int_or_float(value):
    try:
        float(value)
        return True
    except ValueError:
        try:
            int(value)
            return True
        except ValueError:
            return False
    except TypeError:
        print(value)


def remove_string_dots(string):
    new_string = ''
    for letter in string:
        if '.' not in letter:
            new_string = new_string + letter
    return new_string


def commenters_percentage(user_total_followers, posts_data_frame):
    total_comments_percentage = (posts_data_frame['comments'] / user_total_followers) * 100
    median = total_comments_percentage.median()
    return median


def likers_percentage(user_total_followers, posts_data_frame):
    total_likes_percentage = (posts_data_frame['likes'] / user_total_followers) * 100
    median = total_likes_percentage.median()
    return median


def viewers_percentage(user_total_followers, posts_data_frame):
    total_views_percentage = (posts_data_frame['views'] / user_total_followers) * 100
    median = total_views_percentage.median()
    return median


def posts_per_week(posts_data_frame):
    posts = posts_data_frame.shape[0]
    posts -= 1
    weekly_posts = 1
    current_post = 0
    total_weekly_posts = []
    for post in range(posts):
        days = (posts_data_frame['date'][current_post] - posts_data_frame['date'][post + 1])
        weeks = days / np.timedelta64(1, 'W')

        if weeks < 1:
            weekly_posts += 1
        elif weeks >= 2:
            total_weekly_posts.append(weekly_posts)
            weeks -= 1
            for week in range(weeks):
                total_weekly_posts.append(0)
            weekly_posts = 1
        else:
            total_weekly_posts.append(weekly_posts)
            weekly_posts = 1
            current_post = post + 1

    total_weekly_posts.append(weekly_posts)
    total_weekly_posts = pd.Series(total_weekly_posts)
    report_weekly_posts = total_weekly_posts.median()

    return report_weekly_posts


def posts_per_month(posts_data_frame):
    posts = posts_data_frame.shape[0]
    posts -= 1
    monthly_posts = 1
    current_post = 0
    total_monthly_posts = []
    for post in range(posts):
        days = (posts_data_frame['date'][current_post] - posts_data_frame['date'][post + 1])
        months = days / np.timedelta64(1, 'M')

        if months < 1:
            monthly_posts += 1
        elif months >= 2:
            total_monthly_posts.append(monthly_posts)
            months -= 1
            for month in range(months):
                total_monthly_posts.append(0)
            monthly_posts = 1
        else:
            total_monthly_posts.append(monthly_posts)
            monthly_posts = 1
            current_post = post + 1

    total_monthly_posts.append(monthly_posts)
    total_monthly_posts = pd.Series(total_monthly_posts)
    report_monthly_posts = total_monthly_posts.median()

    return report_monthly_posts


def medians_30_days(posts_data_frame):
    posts = posts_data_frame.shape[0]
    posts -= 1
    data_30_days = pd.DataFrame()
    for post in range(posts):
        days = (posts_data_frame['date'][0] - posts_data_frame['date'][post + 1]).days

        if days > 30:
            data_30_days['comments'] = posts_data_frame['comments'][:post]
            data_30_days['likes'] = posts_data_frame['likes'][:post]
            data_30_days['views'] = posts_data_frame['views'][:post]
            break

    if data_30_days.empty:
        data_30_days['comments'] = posts_data_frame['comments']
        data_30_days['likes'] = posts_data_frame['likes']
        data_30_days['views'] = posts_data_frame['views']

    data_30_days_median = data_30_days.median()
    data_30_days_mean = data_30_days.mean()
    return data_30_days_median, data_30_days_mean


def standard_deviations(posts_data_frame):
    all_comments_std = posts_data_frame['comments'].std()
    all_likes_std = posts_data_frame['likes'].std()
    standard_deviation_data = {'comments': all_comments_std, 'likes': all_likes_std}

    return standard_deviation_data


class PandasReportCreator:

    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")['instagram_scraping']
        pd.options.display.max_columns = None

    def get_profiles_data(self):

        all_profiles_usernames = []
        all_profiles_followers = []

        profiles = self.client['scrapped_profiles'].find({})
        for profile in profiles:

            profile_username = profile['username']
            all_profiles_usernames.append(profile_username)

            profile_followers = profile['followers']
            if is_int_or_float(profile_followers):
                profile_followers = remove_string_dots(profile_followers)
                profile_followers = int(profile_followers)
                all_profiles_followers.append(profile_followers)

            all_posts_shortcodes = []
            all_posts_comments = []
            all_posts_likes = []
            all_posts_views = []
            all_posts_dates = []
            all_users_data_frame = {}

            posts = self.client['scrapped_profiles'][profile_username + '_posts'].find({})
            for post in posts:
                post_shortcode = post['shortcode']
                all_posts_shortcodes.append(post_shortcode)

                post_comments = post['comments']
                if is_int_or_float(post_comments):
                    post_comments = remove_string_dots(post_comments)
                    post_comments = int(post_comments)
                all_posts_comments.append(post_comments)

                post_views = post['views']
                if 'Unavailable' not in post_views:
                    if is_int_or_float(post_views):
                        post_views = remove_string_dots(post_views)
                        post_views = int(post_views)
                else:
                    post_views = np.nan
                all_posts_views.append(post_views)

                post_likes = post['likes']
                if 'Unavailable' not in post_likes:
                    if is_int_or_float(post_likes):
                        post_likes = remove_string_dots(post_likes)
                        post_likes = int(post_likes)
                else:
                    post_likes = np.nan
                all_posts_likes.append(post_likes)

                post_date = post['date']
                all_posts_dates.append(post_date)

            all_posts_data = {
                'shortcode': all_posts_shortcodes,
                'comments': all_posts_comments,
                'likes': all_posts_likes,
                'views': all_posts_views,
                'date': all_posts_dates
            }

            all_posts_data_frame = pd.DataFrame(all_posts_data,
                                                columns=['shortcode', 'comments', 'likes', 'views', 'date'])
            all_posts_data_frame['date'] = pd.to_datetime(all_posts_data_frame['date'])
            all_users_data_frame[profile_username] = all_posts_data_frame
            # print(all_posts_data_frame)

            return all_profiles_usernames, all_profiles_followers, all_users_data_frame


prc = PandasReportCreator()

all_users_reports = pd.DataFrame()
usernames, total_followers, users_data_frames = prc.get_profiles_data()
for user in usernames:
    user_data_frame = users_data_frames[user]
    comments_percentage = commenters_percentage(total_followers, user_data_frame)
    likes_percentage = likers_percentage(total_followers, user_data_frame)
    views_percentage = viewers_percentage(total_followers, user_data_frame)
    posts_week = posts_per_week(user_data_frame)
    posts_month = posts_per_month(user_data_frame)
    data_30_days_medians, data_30_days_means = medians_30_days(user_data_frame)
    stds_data = standard_deviations(user_data_frame)
    report_series = pd.Series(data={
        'user': user,
        'comments %': comments_percentage,
        'likes %': likes_percentage,
        'views %': views_percentage,
        'posts/week': posts_week,
        'posts/month': posts_month,
        'comments (monthly median)': data_30_days_medians['comments'],
        'likes (monthly median)': data_30_days_medians['likes'],
        'views (monthly median)': data_30_days_medians['views'],
        'comments (monthly mean)': data_30_days_means['comments'],
        'likes (monthly mean)': data_30_days_means['likes'],
        'views (monthly mean)': data_30_days_means['views'],
        'comments std deviation': stds_data['comments'],
        'likes std deviation': stds_data['likes']
        })
    all_users_reports = all_users_reports.append(report_series, ignore_index=True)

all_users_reports.to_csv('Instagram_users_report.csv', decimal=',', float_format='%.2f', index=False)
