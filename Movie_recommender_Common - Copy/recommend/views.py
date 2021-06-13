import pandas as pd
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.db.models import Case, When
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect

from .forms import *
from .models import Movie, Myrating

moviesLiked = set()


# Create your views here.

def index(request):
    movi = Movie.objects.all()

    action = []
    drama = []
    romance = []

    for movie in movi:
        x = movie.genre.split(',')
        if "Action" in x:
            action.append(movie)
        if "Drama" in x:
            drama.append(movie)
        if "Comedy" in x:
            romance.append(movie)

    # for i in range(4):
    #     movies.append(random.choice(movi))

    Recmovies = recommend(request)
    likedMovies(request)
    print(list(moviesLiked))
    # print("Recommendation Movies: ")
    # print(Recmovies)
    Searchquery = request.GET.get('searchIt')
    # print(Searchquery)
    if Searchquery:
        moviesSearch = Movie.objects.filter(Q(title__icontains=Searchquery)).distinct()
        # print(moviesSearch)
        context = {'moviesLiked': list(set(moviesLiked)), 'moviesBeh': Recmovies[-3:], 'movies': Recmovies[:4],
                   'drama': drama,
                   'action': action,
                   'romance': romance,
                   'moviesSearch': moviesSearch}
        return render(request, 'SidHtml/views/home.html',
                      context)
    # print(drama)
    return render(request, 'SidHtml/views/home.html',
                  {'moviesLiked': list(set(moviesLiked)), 'moviesBeh': Recmovies[-3:], 'movies': Recmovies[:4],
                   'drama': drama,
                   'action': action,
                   'romance': romance})


def likedMovies(request):
    likedList = list(Myrating.objects.filter(user=request.user.id).values())
    for each in likedList:
        movie = Movie.objects.get(id=each['movie_id'])
        if int(each['rating']) > 3:
            moviesLiked.add(movie)
        if int(each['rating']) < 3 and (movie in moviesLiked):
            moviesLiked.remove(movie)

# For similar Movies
def get_similar(movie_name, rating, corrMatrix):
    similar_ratings = corrMatrix[movie_name] * (rating - 2.5)
    similar_ratings = similar_ratings.sort_values(ascending=False)
    return similar_ratings


# Main Recommendation Logic
def recommend(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if not request.user.is_active:
        raise Http404

    movie_rating = pd.DataFrame(list(Myrating.objects.all().values()))

    new_user = movie_rating.user_id.unique().shape[0]
    current_user_id = request.user.id
    # if new user not rated any movie
    if current_user_id > new_user:
        movie = Movie.objects.get(id=19)
        q = Myrating(user=request.user, movie=movie, rating=0)
        q.save()

    userRatings = movie_rating.pivot_table(index=['user_id'], columns=['movie_id'], values='rating')
    userRatings = userRatings.fillna(0, axis=1)
    corrMatrix = userRatings.corr(method='pearson')

    user = pd.DataFrame(list(Myrating.objects.filter(user=request.user).values())).drop(['user_id', 'id'], axis=1)
    user_filtered = [tuple(x) for x in user.values]
    movie_id_watched = [each[0] for each in user_filtered]

    similar_movies = pd.DataFrame()
    for movie, rating in user_filtered:
        similar_movies = similar_movies.append(get_similar(movie, rating, corrMatrix), ignore_index=True)

    movies_id = list(similar_movies.sum().sort_values(ascending=False).index)
    movies_id_recommend = [each for each in movies_id if each not in movie_id_watched]
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(movies_id_recommend)])
    movie_list = list(Movie.objects.filter(id__in=movies_id_recommend).order_by(preserved)[:10])
    return movie_list


# Rating System
def rating(request, m_id):
    movies = get_object_or_404(Movie, id=m_id)
    movie = Movie.objects.get(id=m_id)
    print(m_id)
    if request.method == "POST":
        rate = request.POST.get('rating')
        if Myrating.objects.all().values().filter(movie_id=m_id, user=request.user):
            Myrating.objects.all().values().filter(movie_id=m_id, user=request.user).update(rating=rate)
            print("Rating got: " + str(rate))
        else:
            temp = Myrating(user=request.user, movie=movie, rating=rate)
            temp.save()
            print("else part")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    valList = list(Myrating.objects.filter(user=request.user.id).values())
    print(request.user.id)
    print("val list")
    print(valList)
    movie_rating = 0
    rate_flag = False
    for each in valList:
        if int(each['movie_id']) == int(m_id):
            print("M_ID is :" + str(m_id))
            movie_rating = each['rating']
            print(movie_rating)
            rate_flag = True
            break
    print("Rate Flag:" + str(rate_flag))

    context = {'movies': movies, 'movie_rating': movie_rating, 'rate_flag': rate_flag}

    return render(request, 'SidHtml/views/rating.html', context)


# SignUp
def signUp(request):
    form = UserForm(request.POST or None)

    if form.is_valid():
        user = form.save(commit=True)
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user.set_password(password)
        user.save()
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("index")

    context = {'form': form}

    return render(request, 'SidHtml/views/signup.html', context)


# Login
def Login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect("index")
            else:
                return render(request, 'SidHtml/views/sign.html', {'error_message': 'Your account disable'})
        else:
            return render(request, 'SidHtml/views/sign.html', {'error_message': 'Invalid Login'})

    return render(request, 'SidHtml/views/sign.html')


# Logout user
def Logout(request):
    logout(request)
    moviesLiked = {}
    return redirect("login")
