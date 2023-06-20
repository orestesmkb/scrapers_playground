import json
import time
import requests
import base64

from pymongo import MongoClient
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException


# from pandas_report_creator import PandasReportCreator


# This function setups the webdriver options and configurations
def start_selenium():
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})
    return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)


# This function receives an url and returns a base64 string from the url source
def get_as_base64(url):
    return base64.b64encode(requests.get(url, stream=True).content)


def remove_string_dots(string):
    new_string = ''
    for letter in string:
        if '.' not in letter:
            new_string = new_string + letter
    return new_string


class Main:

    # Initial function with MongoDB, Selenium and Instagram username and password setup
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")['instagram_scraping']
        self.driver = start_selenium()
        with open('login.txt', 'r') as login_file:
            self.username = login_file.readline()
            self.password = login_file.readline()

    # This function verifies if the XPath input exists returning True if it does or False if it does not
    def check_exists_by_xpath(self, xpath):
        try:
            self.driver.find_element(By.XPATH, xpath)
        except NoSuchElementException:
            return False
        return True

    # This function verifies if the CSS path input exists returning True if it does or False if it does not
    def check_exists_by_css(self, css_path):
        try:
            self.driver.find_element(By.CSS_SELECTOR, css_path)
        except NoSuchElementException:
            return False
        return True

    # This function accesses Instagram and log in with user defined username and password
    def login(self):
        driver = self.driver
        driver.get("https://www.instagram.com/")

        time.sleep(3)

        campo_username = driver.find_element(By.NAME, 'username')
        campo_username.click()
        campo_username.clear()
        campo_username.send_keys(self.username)

        campo_password = driver.find_element(By.NAME, 'password')
        campo_password.click()
        campo_password.clear()
        campo_password.send_keys(self.password)
        campo_password.send_keys(Keys.RETURN)
        time.sleep(5)

    # This function gathers basic data from the user's profile and saves it on MongoDB
    def my_profile_data(self):
        driver = self.driver
        profile_url = "https://www.instagram.com/" + self.username

        driver.get(profile_url)
        time.sleep(5)

        my_profile_username = driver.find_element(By.XPATH, "//header/section/div[1]/h2").text
        my_profile_fullname = driver.find_element(By.XPATH, "//header/section/div[2]/h1").text
        my_profile_publications = driver.find_element(By.XPATH, "//header/section/ul/li[1]/span/span").text
        my_profile_followers = driver.find_element(By.XPATH, "//header/section/ul/li[2]/a/span").get_attribute('title')
        my_profile_following = driver.find_element(By.XPATH, "//header/section/ul/li[3]/a/span").text

        # Salva os dados do perfil no banco de dados:
        if not self.client['my_profile'].find_one({'username': my_profile_username}):
            self.client['my_profile'].insert_one(
                {'username': my_profile_username, 'name': my_profile_fullname, 'publications': my_profile_publications,
                 'followers': my_profile_followers, 'following': my_profile_following, 'collected': 0})

        # Verification prints:
        # print(profile_username)
        # print(profile_fullname)
        # print(profile_publications)
        # print(profile_followers)
        # print(profile_following)

    # This function selects a random profile from the explore tab or a profile specified by the user
    def select_profile_to_scrap(self):
        self.driver.get("https://www.instagram.com/explore/")
        time.sleep(5)
        # Pega o primeiro post da página explore:
        first_post = self.driver.find_element(By.XPATH,
                                              "/html/body/div[1]/section/main/div/div[1]/div/div[1]/div[1]/div")
        first_post.click()
        time.sleep(6)

        # Vai no perfil do usuário do primeiro post:
        first_post_user = self.driver.find_element(By.XPATH, "//header/div[2]/div[1]/div[1]/span/a")
        first_post_user.click()
        self.driver.get("https://www.instagram.com/bekamakee_/")
        time.sleep(6)

    # This function gathers basic data from the selected profile and saves it on MongoDB
    def scrap_profile_data(self):
        scrap_username = self.driver.find_element(By.XPATH, "//header/section/div[1]/h2").text
        '/html/body/div[1]/section/main/div/header/section/div[1]/h1'
        scrap_fullname = self.driver.find_element(By.XPATH, "//header/section/div[2]/h1").text
        scrap_publications = self.driver.find_element(By.XPATH, "//header/section/ul/li[1]/span/span").text
        scrap_followers = self.driver.find_element(By.XPATH, "//header/section/ul/li[2]/a/span").get_attribute('title')
        scrap_following = self.driver.find_element(By.XPATH, "//header/section/ul/li[3]/a/span").text
        scrap_profile_pic = self.driver.find_element(By.XPATH, "//header/div/div/span/img").get_attribute('src')

        # Encode profile picture as a base64 string:
        scrap_profile_pic_base64 = get_as_base64(scrap_profile_pic)

        # # Test to check if the string base64 of the profile picture can be decoded successfully:
        # with open('base64_profile_pic.jpg', 'wb') as fh:
        #     fh.write(base64.b64decode(scrap_profile_pic_base64))

        # Verification prints for testing purposes:
        # print(scrap_username)
        # print(scrap_fullname)
        # print(scrap_publications)
        # print(scrap_followers)
        # print(scrap_following)
        # print(scrap_profile_pic_base64)

        # Saves user data in MongoDB:
        if not self.client['scrapped_profiles'].find_one({'username': scrap_username}):
            self.client['scrapped_profiles'].insert_one(
                {'username': scrap_username, 'name': scrap_fullname, 'profile_pic': scrap_profile_pic_base64,
                 'publications': scrap_publications, 'followers': scrap_followers, 'following': scrap_following,
                 'collected': 0})

        return scrap_username, scrap_publications

    # This function receives the CSS path and returns the post type
    def scrap_post_type(self, css_path):
        # Checks post type:
        try:  # If the element exists, get the attribute that defines if it's a video, clip or carousel
            scrap_post_type = self.driver.find_element(By.CSS_SELECTOR, css_path + ' a > div.CzVzU > div > svg') \
                .get_attribute('aria-label')
        except NoSuchElementException:  # If the element does not exist the media is an image
            scrap_post_type = 'Image'  # Mudar a configuração do navegador para inglês

        # print(scrap_post_type)
        return scrap_post_type

    # This function receives the CSS path and the element of the post to scrap, and returns the number of commentaries
    # of the post, obtained through a hover action chain
    def scrap_post_comments(self, css_path):
        time.sleep(1)
        # Obtains the number of comments from the element
        scrap_post_comments = self.driver.find_element(By.CSS_SELECTOR, css_path +
                                                       ' > a > div > ul > li:nth-child(2) > span:nth-child(1)').text
        # print(scrap_post_comments)
        return scrap_post_comments

    # This function receives the post type and obtains the number of likes or views, if they are available
    def scrap_post_views_or_likes(self, scrap_post_type):
        # Obtaining the number of likes or views based on post type:
        if 'Video' in scrap_post_type:
            scrap_post_likes = 'Unavailable'
            scrap_post_views = self.driver.find_element(By.XPATH, '//section[2]/div/span/span').text

        else:
            if self.check_exists_by_xpath('//section[2]/div/div[2]/a/span'):
                scrap_post_likes = self.driver.find_element(By.XPATH, '//section[2]/div/div[2]/a/span').text
            else:
                scrap_post_likes = self.driver.find_element(By.XPATH, '//section[2]/div/div/a/span').text
            scrap_post_views = 'Unavailable'

        # print(scrap_post_likes)
        # print(scrap_post_views)
        return scrap_post_likes, scrap_post_views

    # This function obtains the location of the post, if it is available
    def scrap_post_location(self):
        if self.check_exists_by_xpath('//header/div[2]/div[2]/div[2]/a'):
            scrap_post_location = self.driver.find_element(By.XPATH, '//header/div[2]/div[2]/div[2]/a').text
        else:
            scrap_post_location = 'Unavailable'

        # print(scrap_post_location)
        return scrap_post_location

    # This function obtains the label of the post
    def scrap_post_label(self):
        if self.check_exists_by_xpath('//div[2]/div[1]/ul/div/li/div/div/div[2]/span'):
            scrap_post_label = self.driver.find_element(By.XPATH, '//div[2]/div[1]/ul/div/li/div/div/div[2]/span').text
        else:
            scrap_post_label = 'Unavailable'

        # print(scrap_post_label)
        return scrap_post_label

    # This function obtains the date of the post
    def scrap_post_date(self):
        scrap_post_date = self.driver.find_element(By.XPATH, '//div[2]/div[2]/a/time').get_attribute('datetime')
        # print(scrap_post_date)
        return scrap_post_date

    # This function receives the post type and the shortcode and returns the media in base64 string format and the
    # format of the media as a string
    def scrap_post_media(self, scrap_post_type, scrap_post_shortcode):
        # Obtain media in base64 string format:
        scrap_post_medias_base64 = []
        scrap_post_medias_format = []

        scrap_post_shortcode_json = scrap_post_shortcode + '?__a=1'

        if 'Image' in scrap_post_type:  # If the post type is an image, gets the image as base64 string
            scrap_post_media = self.driver.find_element(By.CSS_SELECTOR, "img[style='object-fit: cover;']") \
                .get_attribute('src')
            scrap_post_media_base64 = get_as_base64(scrap_post_media)  # Encodes in base64 string
            scrap_post_medias_base64.append(scrap_post_media_base64)  # Adds media in the medias list
            scrap_post_medias_format.append('jpg')  # Adds format list to recover the media in the future

        elif 'Carousel' in scrap_post_type:
            # Loops while there is a next post button:
            while self.check_exists_by_css('button div.coreSpriteRightChevron'):
                next_post_sprite = self.driver.find_element(By.CSS_SELECTOR, 'button div.coreSpriteRightChevron')
                next_post_sprite.click()  # Next post button changes to previous post button
                time.sleep(3)

                # Checks if the element is an image and gets it as base64 string
                if self.check_exists_by_css("img[style='object-fit: cover;']"):
                    scrap_post_media = self.driver.find_element(By.CSS_SELECTOR, "img[style='object-fit: cover;']") \
                        .get_attribute('src')
                    scrap_post_media_base64 = get_as_base64(scrap_post_media)
                    scrap_post_medias_base64.append(scrap_post_media_base64)
                    scrap_post_medias_format.append('jpg')

                    # Test to check if the string base64 of the jpg can be decoded successfully:
                    # with open('base64_pic.jpg', 'wb') as fh:
                    #    fh.write(base64.b64decode(scrap_post_media_base64))

                # If it isn't an image it will be a video and will need to get the url past the blob
                else:
                    scrap_post_media = self.driver.find_element(By.CSS_SELECTOR, "video[type='video/mp4']") \
                        .get_attribute('src')
                    scrap_post_media_base64 = get_as_base64(scrap_post_media)
                    scrap_post_medias_base64.append(scrap_post_media_base64)
                    scrap_post_medias_format.append('mp4')

                    # Test to check if the string base64 of the mp4 can be decoded successfully:
                    # with open('base64_video.mp4', 'wb') as fh:
                    #    fh.write(base64.b64decode(scrap_post_media_base64))

        else:  # If the post is not an image or carousel it will be a clip ou video, whose CSS selector is the same
            self.driver.get(scrap_post_shortcode_json)
            scrap_post_json = self.driver.find_element(By.CSS_SELECTOR, 'body > pre').text  # Mudar para o beautifulsoup
            json_wrapped = json.loads(scrap_post_json, encoding='utf8')
            if 'graphql' in json_wrapped.keys():
                graphql = json_wrapped['graphql']
                if 'shortcode_media' in graphql.keys():
                    shortcode_media = graphql['shortcode_media']
                    if 'video_url' in shortcode_media.keys():
                        video_url = shortcode_media['video_url']
                        scrap_post_media_base64 = get_as_base64(video_url)  # Codifica em base64
                        scrap_post_medias_base64.append(scrap_post_media_base64)  # Adiciona na lista de mídias
                        scrap_post_medias_format.append('mp4')  # Segunda lista com os formatos

                        # Test to check if the string base64 of the mp4 can be decoded successfully:
                        with open('base64_video.mp4', 'wb') as fh:
                            fh.write(base64.b64decode(scrap_post_media_base64))

        self.driver.back()
        self.driver.back()
        # print(scrap_post_medias_base64)
        # print(scrap_post_medias_format)
        return scrap_post_medias_base64, scrap_post_medias_format

    # This function receives the number of posts to collect and runs through the collecting functions getting the data
    # requested while saving it on MongoDB for each post in the timeline
    def scrapping_instagram_timeline(self, posts):
        self.select_profile_to_scrap()
        scrap_username, scrap_publications = self.scrap_profile_data()
        total_publications = remove_string_dots(scrap_publications)
        total_publications = int(total_publications)

        if posts > total_publications:
            posts = total_publications

        # Calculates posts vertical and horizontal divisions for CSS path:
        for post in range(posts):
            post_vertical_division = post // 3
            post_horizontal_division = post % 3
            post_vertical_division += 1
            post_horizontal_division += 1
            previous_vertical_division = 1

            # CSS path string formatted with post divisions:
            css_str = 'article > div:nth-child(1) > div > div:nth-child({}) > div:nth-child({})'
            if post_vertical_division > 12:
                post_vertical_division = 13
                constant_css_path = css_str.format(post_vertical_division - 1, post_horizontal_division)
            css_path = css_str.format(post_vertical_division, post_horizontal_division)

            scrap_post_type = self.scrap_post_type(css_path)

            scrap_post = self.driver.find_element(By.CSS_SELECTOR, css_path)

            # if post_vertical_division > previous_vertical_division:
            #     css_selector = self.driver.find_element(locate_with(By.CSS_SELECTOR, 'article').below(scrap_post))
            #     hover = ActionChains(self.driver).move_to_element(css_selector)
            #     hover.perform()

            # Executes hover action chain to get the number of comments
            hover = ActionChains(self.driver).move_to_element(scrap_post)
            hover.perform()

            if post_vertical_division > 12:
                css_path = constant_css_path

            scrap_post_comments = self.scrap_post_comments(css_path)

            scrap_post.click()
            time.sleep(5)

            scrap_post_shortcode = self.driver.find_element(By.CSS_SELECTOR, css_path + '> a').get_attribute('href')
            scrap_post_likes, scrap_post_views = self.scrap_post_views_or_likes(scrap_post_type)
            scrap_post_location = self.scrap_post_location()
            scrap_post_label = self.scrap_post_label()
            scrap_post_date = self.scrap_post_date()

            # scrap_post_medias_base64, scrap_post_medias_format = self.scrap_post_media(
            #     scrap_post_type, scrap_post_shortcode)

            scrap_post_medias_base64 = []
            scrap_post_medias_format = []

            # Saves post data on MongoDB if user is collected and shortcode is not collected already:
            if self.client['scrapped_profiles'].find_one({'username': scrap_username}):
                if not self.client['scrapped_profiles'][scrap_username + '_posts'].find_one(
                        {'shortcode': scrap_post_shortcode}):
                    self.client['scrapped_profiles'][scrap_username + '_posts'].insert_one(
                        {'shortcode': scrap_post_shortcode, 'type': scrap_post_type, 'comments': scrap_post_comments,
                         'likes': scrap_post_likes, 'views': scrap_post_views, 'location': scrap_post_location,
                         'label': scrap_post_label, 'date': scrap_post_date, 'media': scrap_post_medias_base64,
                         'format': scrap_post_medias_format, 'collected': 0})
                else:
                    pass
                    # self.client['scrapped_profiles'][scrap_username + '_posts'].update_one()
                    # self.client['scrapped_profiles'][scrap_username + '_posts'].replace_one()

            # Finds the close button and closes the selected post to continue in the next iteration:
            time.sleep(1)
            scrap_close_post = self.driver.find_element(By.XPATH, '/html/body/div[6]/div[3]/button')
            scrap_close_post.click()


main = Main()

main.login()
# main.my_profile_data()
number_of_posts = 100
main.scrapping_instagram_timeline(number_of_posts)
main.driver.close()
main.driver.quit()

# call scrap reporter
# report = PandasReportCreator()

raise SystemExit()

# Two different ways to download mp4 media:

# needs to import urllib.request
# urllib.request.urlretrieve(scrap_post_media, 'base64_video.mp4')

# downloaded_obj = requests.get(scrap_post_media)
# with open("base64_video.mp4", "wb") as file:
#     file.write(downloaded_obj.content)
