import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/shared/stores/auth'
import { useAuthGuard } from '@/shared/composables/usePermissions'
import { message } from 'ant-design-vue'

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
    meta: {
      requiresAuth: true,
      permissions: ['管理赛事'],
    },
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
      {
        path: ':id/edit',
        name: 'EditTournament',
        meta: {
          requiresAuth: true,
          permissions: ['管理赛事'],
        },
        component: () => import('@/features/tournaments/views/EditTournamentView.vue'),
      },
      {
        path: ':id/rooms',
        name: 'TournamentRooms',
        meta: { requiresAuth: true },
        component: () => import('@/features/tournaments/views/TournamentRoomsView.vue'),
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
        path: 'pool',
        name: 'PlayerPool',
        meta: { requiresAuth: true },
        component: () => import('@/features/players/views/PlayerPoolView.vue'),
      },
      {
        path: 'register',
        name: 'PlayerRegistration',
        meta: { requiresAuth: true },
        component: () => import('@/features/players/views/PlayerRegistrationView.vue'),
      },
      {
        path: ':id',
        name: 'PlayerProfile',
        component: () => import('@/features/players/views/PlayerProfileView.vue'),
      },
    ],
  },
  {
    path: '/matches',
    name: 'Matches',
    children: [
      {
        path: ':id',
        name: 'MatchDetail',
        component: () => import('@/features/matches/views/MatchDetailView.vue'),
      },
      {
        path: 'bp-rooms',
        name: 'BPRooms',
        meta: { requiresAuth: true },
        component: () => import('@/features/matches/views/BPRoomListView.vue'),
      },
      {
        path: 'bp-room/:roomId',
        name: 'BPRoomDetail',
        meta: { requiresAuth: true },
        component: () => import('@/features/matches/views/BPRoomDetailView.vue'),
      },
      {
        path: 'bp-room/:roomId/join',
        name: 'JoinBPRoom',
        meta: { requiresAuth: true },
        component: () => import('@/features/matches/views/JoinBPRoomView.vue'),
      },
    ],
  },
  {
    path: '/tournaments/:tournamentId/matches/:matchId/room',
    name: 'MatchRoom',
    meta: { 
      requiresAuth: true,
      requiresMatchAccess: true 
    },
    component: () => import('@/features/matches/views/MatchRoomView.vue'),
  },
  {
    path: '/tournaments/:tournamentId/matches/:matchId/spectate',
    name: 'MatchSpectate',
    meta: { requiresAuth: false },
    component: () => import('@/features/matches/views/MatchRoomView.vue'),
  },
  {
    path: '/tournaments/:tournamentId/matches/:matchId/bp',
    name: 'BanPick',
    meta: { 
      requiresAuth: true,
      requiresMatchAccess: true 
    },
    component: () => import('@/features/matches/views/BanPickView.vue'),
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
        path: 'tournament/:id',
        name: 'HallTournamentDetail',
        component: () => import('@/features/tournaments/views/TournamentDetailView.vue'),
        props: { fromHall: true },
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
    path: '/admin',
    name: 'Admin',
    meta: {
      requiresAuth: true,
      requireAdmin: true,
      permissions: ['管理系统', '管理用户', '管理角色', '管理赛区'],
    },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: () => import('@/features/admin/views/DashboardView.vue'),
        meta: { requireAdmin: true },
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/features/admin/views/UsersView.vue'),
        meta: { permissions: ['管理用户'] },
      },
      {
        path: 'roles',
        name: 'AdminRoles',
        component: () => import('@/features/admin/views/RolesView.vue'),
        meta: { permissions: ['管理角色'] },
      },
      {
        path: 'regions',
        name: 'AdminRegions',
        component: () => import('@/features/admin/views/RegionsView.vue'),
        meta: { permissions: ['管理赛区'] },
      },
      {
        path: 'system',
        name: 'AdminSystem',
        component: () => import('@/features/admin/views/SystemView.vue'),
        meta: { permissions: ['管理系统'] },
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

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 等待认证状态初始化
  if (authStore.token && !authStore.user) {
    try {
      await authStore.initAuth()
    } catch (error) {
      console.warn('Failed to initialize auth:', error)
    }
  }

  const { guardRoute } = useAuthGuard()

  // 基础认证检查
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // 比赛房间访问权限检查
  if (to.meta.requiresMatchAccess && to.name === 'MatchRoom') {
    // TODO: 实现比赛房间访问权限检查
    // 这里应该检查用户是否为参赛者或管理员
    const matchId = to.params.matchId as string
    const tournamentId = to.params.tournamentId as string
    
    if (!authStore.isAuthenticated) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
    
    // 暂时允许所有已登录用户访问，实际应该检查参赛权限
    // 在实际应用中，这里应该调用API检查用户是否有权限进入特定比赛房间
    console.log(`检查用户是否可以进入比赛房间: tournament=${tournamentId}, match=${matchId}`)
  }

  // 如果已登录但需要权限检查
  if (
    authStore.isAuthenticated &&
    (to.meta.requireAdmin || to.meta.permissions || to.meta.roles || to.meta.minLevel)
  ) {
    const guardResult = guardRoute({
      requireAuth: !!to.meta.requiresAuth,
      requireAdmin: !!to.meta.requireAdmin,
      permissions: to.meta.permissions as string[],
      roles: to.meta.roles as string[],
      minLevel: to.meta.minLevel as number,
    })

    if (!guardResult.allowed) {
      message.error({
        content: guardResult.reason || '权限不足',
        duration: 2.5, // 设置显示时长为2.5秒
      })
      next({ name: 'Home' })
      return
    }
  }

  next()
})

export default router
