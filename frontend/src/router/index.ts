import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/shared/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
  },
  {
    path: '/auth',
    name: 'Auth',
    children: [
      {
        path: 'login',
        name: 'Login',
        component: () => import('@/features/auth/views/LoginView.vue'),
      },
      {
        path: 'register',
        name: 'Register',
        component: () => import('@/features/auth/views/RegisterView.vue'),
      },
    ],
  },
  {
    path: '/teams',
    name: 'Teams',
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'TeamsList',
        component: () => import('@/features/teams/views/TeamsListView.vue'),
      },
      {
        path: 'create',
        name: 'CreateTeam',
        component: () => import('@/features/teams/views/CreateTeamView.vue'),
      },
      {
        path: ':id',
        name: 'TeamDetail',
        component: () => import('@/features/teams/views/TeamDetailView.vue'),
      },
    ],
  },
  {
    path: '/tournaments',
    name: 'Tournaments',
    children: [
      {
        path: '',
        name: 'TournamentsList',
        component: () => import('@/features/tournaments/views/TournamentsListView.vue'),
      },
      {
        path: 'create',
        name: 'CreateTournament',
        meta: { requiresAuth: true },
        component: () => import('@/features/tournaments/views/CreateTournamentView.vue'),
      },
      {
        path: ':id',
        name: 'TournamentDetail',
        component: () => import('@/features/tournaments/views/TournamentDetailView.vue'),
      },
    ],
  },
  {
    path: '/players',
    name: 'Players',
    children: [
      {
        path: '',
        name: 'PlayersList',
        component: () => import('@/features/players/views/PlayerProfileView.vue'),
      },
      {
        path: ':id',
        name: 'PlayerProfile',
        component: () => import('@/features/players/views/PlayerProfileView.vue'),
      },
    ],
  },
  {
    path: '/matches/:id',
    name: 'MatchDetail',
    component: () => import('@/features/matches/views/MatchDetailView.vue'),
  },
  {
    path: '/live',
    name: 'Live',
    children: [
      {
        path: '',
        name: 'LiveList',
        component: () => import('@/features/live/views/LiveView.vue'),
      },
      {
        path: ':id',
        name: 'LiveStream',
        component: () => import('@/features/live/views/LiveView.vue'),
      },
    ],
  },
  {
    path: '/schedule',
    name: 'Schedule',
    component: () => import('@/features/schedule/views/ScheduleView.vue'),
  },
  {
    path: '/recruitment',
    name: 'Recruitment',
    children: [
      {
        path: '',
        name: 'RecruitmentList',
        component: () => import('@/features/recruitment/views/RecruitmentView.vue'),
      },
      {
        path: 'create',
        name: 'CreateRecruitment',
        meta: { requiresAuth: true },
        component: () => import('@/features/recruitment/views/RecruitmentView.vue'),
      },
      {
        path: 'my',
        name: 'MyRecruitments',
        meta: { requiresAuth: true },
        component: () => import('@/features/recruitment/views/RecruitmentView.vue'),
      },
      {
        path: ':id',
        name: 'RecruitmentDetail',
        component: () => import('@/features/recruitment/views/RecruitmentView.vue'),
      },
    ],
  },
  {
    path: '/hall',
    name: 'Hall',
    children: [
      {
        path: '',
        name: 'HallMain',
        component: () => import('@/features/hall/views/HallView.vue'),
      },
      {
        path: 'my-matches',
        name: 'MyMatches',
        meta: { requiresAuth: true },
        component: () => import('@/features/hall/views/HallView.vue'),
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router