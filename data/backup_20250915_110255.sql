--
-- PostgreSQL database dump
--

\restrict HNEivBQkdgixIN66acgu0u01enWqRGFBYTquQZ8p6V1k0qbrk0v5OhTHr7CfS0f

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: checkinstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.checkinstatus AS ENUM (
    'not_checked_in',
    'checked_in'
);


ALTER TYPE public.checkinstatus OWNER TO postgres;

--
-- Name: contractstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.contractstatus AS ENUM (
    'FREE',
    'LOCKED',
    'PENDING'
);


ALTER TYPE public.contractstatus OWNER TO postgres;

--
-- Name: player_position; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.player_position AS ENUM (
    'TOP',
    'JUNGLE',
    'MIDDLE',
    'BOTTOM',
    'UTILITY'
);


ALTER TYPE public.player_position OWNER TO postgres;

--
-- Name: tournament_matchstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tournament_matchstatus AS ENUM (
    'scheduled',
    'waiting_for_checkin',
    'checking_in',
    'ready',
    'in_progress',
    'completed',
    'cancelled'
);


ALTER TYPE public.tournament_matchstatus OWNER TO postgres;

--
-- Name: tournament_registrationstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tournament_registrationstatus AS ENUM (
    'pending',
    'confirmed',
    'rejected',
    'withdrawn'
);


ALTER TYPE public.tournament_registrationstatus OWNER TO postgres;

--
-- Name: tournamentformat; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tournamentformat AS ENUM (
    'single_elimination',
    'double_elimination',
    'round_robin',
    'swiss',
    'custom'
);


ALTER TYPE public.tournamentformat OWNER TO postgres;

--
-- Name: tournamentstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tournamentstatus AS ENUM (
    'draft',
    'upcoming',
    'registration_open',
    'registration_closed',
    'ongoing',
    'completed',
    'cancelled'
);


ALTER TYPE public.tournamentstatus OWNER TO postgres;

--
-- Name: tournamenttype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.tournamenttype AS ENUM (
    'team_based',
    'solo_based'
);


ALTER TYPE public.tournamenttype OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: match_check_ins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.match_check_ins (
    id uuid NOT NULL,
    match_id uuid NOT NULL,
    participant_id uuid NOT NULL,
    team_id uuid,
    status character varying(20) NOT NULL,
    checked_in_at timestamp without time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.match_check_ins OWNER TO postgres;

--
-- Name: matches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.matches (
    id integer NOT NULL,
    tournament_id uuid,
    season_id integer,
    team_a_id integer NOT NULL,
    team_b_id integer NOT NULL,
    scheduled_at timestamp with time zone NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    status character varying(20) DEFAULT 'SCHEDULED'::character varying NOT NULL,
    result character varying(20),
    team_a_score integer DEFAULT 0,
    team_b_score integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.matches OWNER TO postgres;

--
-- Name: matches_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.matches_id_seq OWNER TO postgres;

--
-- Name: matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.matches_id_seq OWNED BY public.matches.id;


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.permissions (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    resource character varying(50) NOT NULL,
    action character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.permissions OWNER TO postgres;

--
-- Name: permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.permissions_id_seq OWNER TO postgres;

--
-- Name: permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.permissions_id_seq OWNED BY public.permissions.id;


--
-- Name: player_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.player_profiles (
    id integer NOT NULL,
    profile_id character varying(50) NOT NULL,
    user_id integer NOT NULL,
    player_name character varying(100) NOT NULL,
    summoner_name character varying(100) NOT NULL,
    "position" public.player_position NOT NULL,
    region_id integer NOT NULL,
    current_team_id integer,
    current_rating double precision DEFAULT 1200.0 NOT NULL,
    peak_rating double precision DEFAULT 1200.0 NOT NULL,
    rank_tier character varying(20),
    rank_division character varying(10),
    league_points integer DEFAULT 0,
    contract_status public.contractstatus DEFAULT 'FREE'::public.contractstatus NOT NULL,
    total_matches integer DEFAULT 0 NOT NULL,
    total_wins integer DEFAULT 0 NOT NULL,
    total_losses integer DEFAULT 0 NOT NULL,
    last_active timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    description text,
    locked_rating double precision,
    contract_start timestamp with time zone
);


ALTER TABLE public.player_profiles OWNER TO postgres;

--
-- Name: player_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.player_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.player_profiles_id_seq OWNER TO postgres;

--
-- Name: player_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.player_profiles_id_seq OWNED BY public.player_profiles.id;


--
-- Name: regions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.regions (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    admin_user_id integer DEFAULT 1 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    max_teams_per_season integer DEFAULT 16 NOT NULL,
    allow_public_registration boolean DEFAULT true NOT NULL
);


ALTER TABLE public.regions OWNER TO postgres;

--
-- Name: regions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.regions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.regions_id_seq OWNER TO postgres;

--
-- Name: regions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.regions_id_seq OWNED BY public.regions.id;


--
-- Name: role_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.role_permissions (
    id integer NOT NULL,
    role_id integer NOT NULL,
    permission_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.role_permissions OWNER TO postgres;

--
-- Name: role_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.role_permissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.role_permissions_id_seq OWNER TO postgres;

--
-- Name: role_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.role_permissions_id_seq OWNED BY public.role_permissions.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description text,
    level integer DEFAULT 0 NOT NULL,
    is_system boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.roles_id_seq OWNER TO postgres;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: seasons; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.seasons (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    region_id integer NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    status character varying(20) DEFAULT 'UPCOMING'::character varying NOT NULL,
    max_teams integer DEFAULT 16 NOT NULL,
    registration_deadline date NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.seasons OWNER TO postgres;

--
-- Name: seasons_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.seasons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.seasons_id_seq OWNER TO postgres;

--
-- Name: seasons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.seasons_id_seq OWNED BY public.seasons.id;


--
-- Name: team_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.team_members (
    id integer NOT NULL,
    team_id integer NOT NULL,
    player_profile_id integer NOT NULL,
    "position" character varying(20) DEFAULT 'FILL'::character varying NOT NULL,
    is_captain boolean DEFAULT false NOT NULL,
    is_substitute boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    joined_at timestamp with time zone DEFAULT now() NOT NULL,
    left_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.team_members OWNER TO postgres;

--
-- Name: team_members_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.team_members_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.team_members_id_seq OWNER TO postgres;

--
-- Name: team_members_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.team_members_id_seq OWNED BY public.team_members.id;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teams (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    tag character varying(10) NOT NULL,
    description text,
    region_id integer NOT NULL,
    captain_user_id integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_recruiting boolean DEFAULT false NOT NULL,
    min_rank_requirement character varying(20),
    max_members integer DEFAULT 5 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.teams OWNER TO postgres;

--
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.teams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.teams_id_seq OWNER TO postgres;

--
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- Name: tournament_matches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tournament_matches (
    id uuid NOT NULL,
    tournament_id uuid NOT NULL,
    round_number integer DEFAULT 1 NOT NULL,
    match_number integer,
    blue_side_id uuid NOT NULL,
    red_side_id uuid NOT NULL,
    status character varying(30) NOT NULL,
    room_id uuid,
    scheduled_time timestamp without time zone NOT NULL,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    winner_id uuid,
    loser_id uuid,
    match_data json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tournament_matches OWNER TO postgres;

--
-- Name: tournament_registrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tournament_registrations (
    id uuid NOT NULL,
    tournament_id uuid NOT NULL,
    participant_id uuid NOT NULL,
    participant_type character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    registered_by integer NOT NULL,
    registered_at timestamp without time zone NOT NULL,
    is_admin_registered boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tournament_registrations OWNER TO postgres;

--
-- Name: tournaments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tournaments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    tournament_type public.tournamenttype DEFAULT 'team_based'::public.tournamenttype NOT NULL,
    region_id integer NOT NULL,
    created_by integer NOT NULL,
    registration_start timestamp with time zone NOT NULL,
    registration_end timestamp with time zone NOT NULL,
    tournament_start timestamp with time zone NOT NULL,
    tournament_end timestamp with time zone NOT NULL,
    format public.tournamentformat DEFAULT 'single_elimination'::public.tournamentformat NOT NULL,
    max_participants integer DEFAULT 16 NOT NULL,
    team_size integer DEFAULT 5,
    min_rank character varying(20),
    max_rank character varying(20),
    status public.tournamentstatus DEFAULT 'draft'::public.tournamentstatus NOT NULL,
    registration_count integer DEFAULT 0 NOT NULL,
    logo_url character varying(500),
    banner_url character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tournaments OWNER TO postgres;

--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_roles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    role_id integer NOT NULL,
    region_id integer,
    granted_by_user_id integer,
    is_active boolean DEFAULT true NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    granted_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_roles OWNER TO postgres;

--
-- Name: user_roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_roles_id_seq OWNER TO postgres;

--
-- Name: user_roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_roles_id_seq OWNED BY public.user_roles.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    riot_summoner_name character varying(100),
    last_login_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: matches id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches ALTER COLUMN id SET DEFAULT nextval('public.matches_id_seq'::regclass);


--
-- Name: permissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions ALTER COLUMN id SET DEFAULT nextval('public.permissions_id_seq'::regclass);


--
-- Name: player_profiles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_profiles ALTER COLUMN id SET DEFAULT nextval('public.player_profiles_id_seq'::regclass);


--
-- Name: regions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.regions ALTER COLUMN id SET DEFAULT nextval('public.regions_id_seq'::regclass);


--
-- Name: role_permissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions ALTER COLUMN id SET DEFAULT nextval('public.role_permissions_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: seasons id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seasons ALTER COLUMN id SET DEFAULT nextval('public.seasons_id_seq'::regclass);


--
-- Name: team_members id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members ALTER COLUMN id SET DEFAULT nextval('public.team_members_id_seq'::regclass);


--
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- Name: user_roles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles ALTER COLUMN id SET DEFAULT nextval('public.user_roles_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
\.


--
-- Data for Name: match_check_ins; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.match_check_ins (id, match_id, participant_id, team_id, status, checked_in_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: matches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.matches (id, tournament_id, season_id, team_a_id, team_b_id, scheduled_at, started_at, completed_at, status, result, team_a_score, team_b_score, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.permissions (id, name, description, resource, action, created_at, updated_at) FROM stdin;
1	管理系统	系统管理权限	SYSTEM	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
2	管理用户	用户管理权限	USER	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
3	管理角色	角色管理权限	ROLE	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
4	管理赛区	赛区管理权限	REGION	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
5	创建赛区	创建赛区权限	REGION	CREATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
6	查看赛区	查看赛区权限	REGION	READ	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
7	更新赛区	更新赛区权限	REGION	UPDATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
8	删除赛区	删除赛区权限	REGION	DELETE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
9	创建选手	创建选手权限	PLAYER	CREATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
10	管理选手	选手管理权限	PLAYER	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
11	查看选手档案	查看选手档案权限	PLAYER_PROFILE	READ	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
12	更新选手档案	更新选手档案权限	PLAYER_PROFILE	UPDATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
13	管理选手评分	选手评分管理权限	PLAYER_RATING	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
14	创建战队	创建战队权限	TEAM	CREATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
15	管理战队	战队管理权限	TEAM	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
16	查看战队	查看战队权限	TEAM	READ	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
17	更新战队	更新战队权限	TEAM	UPDATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
18	删除战队	删除战队权限	TEAM	DELETE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
19	管理队员	队员管理权限	TEAM_MEMBER	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
20	审批入队申请	入队申请审批权限	TEAM_APPLICATION	APPROVE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
21	拒绝入队申请	入队申请拒绝权限	TEAM_APPLICATION	REJECT	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
22	创建比赛	创建比赛权限	MATCH	CREATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
23	管理比赛	比赛管理权限	MATCH	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
24	查看比赛	查看比赛权限	MATCH	READ	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
25	更新比赛结果	更新比赛结果权限	MATCH_RESULT	UPDATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
26	管理比赛数据	比赛数据管理权限	MATCH_DATA	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
27	创建赛事	创建赛事权限	TOURNAMENT	CREATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
28	管理赛事	赛事管理权限	TOURNAMENT	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
29	查看赛事	查看赛事权限	TOURNAMENT	READ	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
30	更新赛事	更新赛事权限	TOURNAMENT	UPDATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
31	删除赛事	删除赛事权限	TOURNAMENT	DELETE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
32	赛事报名	赛事报名权限	TOURNAMENT_REGISTRATION	CREATE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
33	管理赛事报名	赛事报名管理权限	TOURNAMENT_REGISTRATION	MANAGE	2025-09-11 06:13:30.64842+00	2025-09-11 06:13:30.64842+00
\.


--
-- Data for Name: player_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.player_profiles (id, profile_id, user_id, player_name, summoner_name, "position", region_id, current_team_id, current_rating, peak_rating, rank_tier, rank_division, league_points, contract_status, total_matches, total_wins, total_losses, last_active, created_at, updated_at, description, locked_rating, contract_start) FROM stdin;
\.


--
-- Data for Name: regions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.regions (id, name, description, created_at, updated_at, admin_user_id, is_active, max_teams_per_season, allow_public_registration) FROM stdin;
1	测试赛区	用于测试的赛区	2025-09-11 05:59:43.552965+00	2025-09-11 05:59:43.552965+00	1	t	16	t
2	华东赛区	华东地区电竞赛区	2025-09-11 07:43:01.739581+00	2025-09-11 07:43:01.739581+00	1	t	32	t
\.


--
-- Data for Name: role_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.role_permissions (id, role_id, permission_id, created_at) FROM stdin;
187	1	1	2025-09-11 06:13:30.688509+00
188	1	2	2025-09-11 06:13:30.688509+00
189	1	3	2025-09-11 06:13:30.688509+00
190	1	4	2025-09-11 06:13:30.688509+00
191	1	5	2025-09-11 06:13:30.688509+00
192	1	6	2025-09-11 06:13:30.688509+00
193	1	7	2025-09-11 06:13:30.688509+00
194	1	8	2025-09-11 06:13:30.688509+00
195	1	9	2025-09-11 06:13:30.688509+00
196	1	10	2025-09-11 06:13:30.688509+00
197	1	11	2025-09-11 06:13:30.688509+00
198	1	12	2025-09-11 06:13:30.688509+00
199	1	13	2025-09-11 06:13:30.688509+00
200	1	14	2025-09-11 06:13:30.688509+00
201	1	15	2025-09-11 06:13:30.688509+00
202	1	16	2025-09-11 06:13:30.688509+00
203	1	17	2025-09-11 06:13:30.688509+00
204	1	18	2025-09-11 06:13:30.688509+00
205	1	19	2025-09-11 06:13:30.688509+00
206	1	20	2025-09-11 06:13:30.688509+00
207	1	21	2025-09-11 06:13:30.688509+00
208	1	22	2025-09-11 06:13:30.688509+00
209	1	23	2025-09-11 06:13:30.688509+00
210	1	24	2025-09-11 06:13:30.688509+00
211	1	25	2025-09-11 06:13:30.688509+00
212	1	26	2025-09-11 06:13:30.688509+00
213	1	27	2025-09-11 06:13:30.688509+00
214	1	28	2025-09-11 06:13:30.688509+00
215	1	29	2025-09-11 06:13:30.688509+00
216	1	30	2025-09-11 06:13:30.688509+00
217	1	31	2025-09-11 06:13:30.688509+00
218	1	32	2025-09-11 06:13:30.688509+00
219	1	33	2025-09-11 06:13:30.688509+00
220	2	4	2025-09-11 06:13:30.688509+00
221	2	5	2025-09-11 06:13:30.688509+00
222	2	6	2025-09-11 06:13:30.688509+00
223	2	7	2025-09-11 06:13:30.688509+00
224	2	8	2025-09-11 06:13:30.688509+00
225	2	9	2025-09-11 06:13:30.688509+00
226	2	10	2025-09-11 06:13:30.688509+00
227	2	11	2025-09-11 06:13:30.688509+00
228	2	12	2025-09-11 06:13:30.688509+00
229	2	13	2025-09-11 06:13:30.688509+00
230	2	14	2025-09-11 06:13:30.688509+00
231	2	15	2025-09-11 06:13:30.688509+00
232	2	16	2025-09-11 06:13:30.688509+00
233	2	17	2025-09-11 06:13:30.688509+00
234	2	18	2025-09-11 06:13:30.688509+00
235	2	19	2025-09-11 06:13:30.688509+00
236	2	20	2025-09-11 06:13:30.688509+00
237	2	21	2025-09-11 06:13:30.688509+00
238	2	22	2025-09-11 06:13:30.688509+00
239	2	23	2025-09-11 06:13:30.688509+00
240	2	24	2025-09-11 06:13:30.688509+00
241	2	25	2025-09-11 06:13:30.688509+00
242	2	26	2025-09-11 06:13:30.688509+00
243	2	27	2025-09-11 06:13:30.688509+00
244	2	28	2025-09-11 06:13:30.688509+00
245	2	29	2025-09-11 06:13:30.688509+00
246	2	30	2025-09-11 06:13:30.688509+00
247	2	31	2025-09-11 06:13:30.688509+00
248	2	32	2025-09-11 06:13:30.688509+00
249	2	33	2025-09-11 06:13:30.688509+00
250	3	11	2025-09-11 06:13:30.688509+00
251	3	12	2025-09-11 06:13:30.688509+00
252	3	14	2025-09-11 06:13:30.688509+00
253	3	15	2025-09-11 06:13:30.688509+00
254	3	16	2025-09-11 06:13:30.688509+00
255	3	17	2025-09-11 06:13:30.688509+00
256	3	19	2025-09-11 06:13:30.688509+00
257	3	20	2025-09-11 06:13:30.688509+00
258	3	21	2025-09-11 06:13:30.688509+00
259	3	24	2025-09-11 06:13:30.688509+00
260	3	26	2025-09-11 06:13:30.688509+00
261	3	29	2025-09-11 06:13:30.688509+00
262	3	32	2025-09-11 06:13:30.688509+00
263	4	11	2025-09-11 06:13:30.688509+00
264	4	12	2025-09-11 06:13:30.688509+00
265	4	16	2025-09-11 06:13:30.688509+00
266	4	24	2025-09-11 06:13:30.688509+00
267	4	29	2025-09-11 06:13:30.688509+00
268	4	32	2025-09-11 06:13:30.688509+00
269	5	11	2025-09-11 06:13:30.688509+00
270	5	12	2025-09-11 06:13:30.688509+00
271	5	16	2025-09-11 06:13:30.688509+00
272	5	24	2025-09-11 06:13:30.688509+00
273	5	29	2025-09-11 06:13:30.688509+00
274	5	32	2025-09-11 06:13:30.688509+00
275	6	6	2025-09-11 06:13:30.688509+00
276	6	11	2025-09-11 06:13:30.688509+00
277	6	16	2025-09-11 06:13:30.688509+00
278	6	24	2025-09-11 06:13:30.688509+00
279	6	29	2025-09-11 06:13:30.688509+00
\.


--
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (id, name, description, level, is_system, created_at, updated_at) FROM stdin;
1	超级管理员	系统超级管理员，拥有全局管理权限	100	t	2025-09-11 05:17:21.711464+00	2025-09-11 05:17:21.711464+00
2	赛区管理员	赛区管理员，拥有单个赛区的管理权限	80	t	2025-09-11 05:17:21.711464+00	2025-09-11 05:17:21.711464+00
3	队长	战队队长，拥有战队管理权限	60	t	2025-09-11 05:17:21.711464+00	2025-09-11 05:17:21.711464+00
4	队员	战队队员，拥有战队成员权限	40	t	2025-09-11 05:17:21.711464+00	2025-09-11 05:17:21.711464+00
5	选手	注册选手，拥有选手基础权限	20	t	2025-09-11 05:17:21.711464+00	2025-09-11 05:17:21.711464+00
6	用户	基础用户，拥有基本浏览权限	10	t	2025-09-11 05:17:21.711464+00	2025-09-11 05:17:21.711464+00
\.


--
-- Data for Name: seasons; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.seasons (id, name, description, region_id, start_date, end_date, status, max_teams, registration_deadline, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: team_members; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.team_members (id, team_id, player_profile_id, "position", is_captain, is_substitute, is_active, joined_at, left_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teams (id, name, tag, description, region_id, captain_user_id, is_active, is_recruiting, min_rank_requirement, max_members, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tournament_matches; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournament_matches (id, tournament_id, round_number, match_number, blue_side_id, red_side_id, status, room_id, scheduled_time, started_at, completed_at, winner_id, loser_id, match_data, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tournament_registrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournament_registrations (id, tournament_id, participant_id, participant_type, status, registered_by, registered_at, is_admin_registered, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tournaments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tournaments (id, name, description, tournament_type, region_id, created_by, registration_start, registration_end, tournament_start, tournament_end, format, max_participants, team_size, min_rank, max_rank, status, registration_count, logo_url, banner_url, created_at, updated_at) FROM stdin;
562088f8-067c-418d-b933-665b8c4477e6	第一届赛事		solo_based	2	5	2025-09-22 02:00:00+00	2025-09-26 02:00:00+00	2025-09-27 02:00:00+00	2025-09-28 02:00:00+00	single_elimination	16	5			registration_closed	0			2025-09-15 01:04:17.942795+00	2025-09-15 01:48:50.034836+00
\.


--
-- Data for Name: user_roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_roles (id, user_id, role_id, region_id, granted_by_user_id, is_active, expires_at, created_at, updated_at, granted_at) FROM stdin;
1	1	1	\N	1	t	\N	2025-09-11 05:17:45.798374+00	2025-09-11 05:17:45.798374+00	2025-09-11 06:40:06.244308+00
3	4	6	\N	\N	t	\N	2025-09-11 06:42:30.921828+00	2025-09-11 06:42:30.921828+00	2025-09-11 06:42:30.921828+00
2	3	1	\N	\N	t	\N	2025-09-11 06:40:43.327395+00	2025-09-11 06:40:43.327395+00	2025-09-11 06:40:43.327395+00
4	5	1	\N	\N	t	\N	2025-09-12 14:12:13.828263+00	2025-09-12 14:12:13.828263+00	2025-09-12 14:12:13.828263+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, username, email, password_hash, is_active, is_verified, created_at, updated_at, riot_summoner_name, last_login_at) FROM stdin;
1	admin	admin@flyesports.com	$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewrBdXuu0/RB0QKm	t	t	2025-09-11 05:17:45.798374+00	2025-09-11 05:17:45.798374+00	\N	2025-09-11 14:34:54+00
4	testuser123	testuser123@example.com	$2b$12$fkGDkTmDDKRKB0opzWFed.TpWzgfNt0rTldxkk72haYdDhvSLrCR6	t	f	2025-09-11 06:42:30.916126+00	2025-09-11 06:42:30.916126+00	TestSummoner123	\N
3	maple	Mapleccs@outlook.com	$2b$12$Jk8vLbxxd28AtI924i91/eq5TxNDEMYj6PLwoKd4xZ27IXwG0jzWG	t	t	2025-09-11 06:34:34.460114+00	2025-09-12 13:34:18.059651+00	\N	2025-09-12 13:34:18.056766+00
5	mapleCCS	468355490@qq.com	$2b$12$bq5VPix47u0.7p4pfhCckefihAppOrUZmpluPA4WyMq/I3NlkgvAC	t	f	2025-09-12 14:12:13.810864+00	2025-09-15 02:23:10.970849+00	\N	2025-09-15 02:23:10.966912+00
\.


--
-- Name: matches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.matches_id_seq', 1, false);


--
-- Name: permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.permissions_id_seq', 33, true);


--
-- Name: player_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.player_profiles_id_seq', 1, false);


--
-- Name: regions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.regions_id_seq', 2, true);


--
-- Name: role_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.role_permissions_id_seq', 279, true);


--
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_id_seq', 1, false);


--
-- Name: seasons_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.seasons_id_seq', 1, false);


--
-- Name: team_members_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.team_members_id_seq', 1, false);


--
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.teams_id_seq', 1, false);


--
-- Name: user_roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_roles_id_seq', 4, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 5, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: match_check_ins match_check_ins_match_id_participant_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.match_check_ins
    ADD CONSTRAINT match_check_ins_match_id_participant_id_key UNIQUE (match_id, participant_id);


--
-- Name: match_check_ins match_check_ins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.match_check_ins
    ADD CONSTRAINT match_check_ins_pkey PRIMARY KEY (id);


--
-- Name: matches matches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_name_key UNIQUE (name);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (id);


--
-- Name: permissions permissions_resource_action_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT permissions_resource_action_key UNIQUE (resource, action);


--
-- Name: player_profiles player_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_profiles
    ADD CONSTRAINT player_profiles_pkey PRIMARY KEY (id);


--
-- Name: player_profiles player_profiles_profile_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_profiles
    ADD CONSTRAINT player_profiles_profile_id_key UNIQUE (profile_id);


--
-- Name: regions regions_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT regions_name_key UNIQUE (name);


--
-- Name: regions regions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT regions_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (id);


--
-- Name: role_permissions role_permissions_role_id_permission_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_permission_id_key UNIQUE (role_id, permission_id);


--
-- Name: roles roles_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_name_key UNIQUE (name);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: seasons seasons_name_region_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT seasons_name_region_id_key UNIQUE (name, region_id);


--
-- Name: seasons seasons_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT seasons_pkey PRIMARY KEY (id);


--
-- Name: team_members team_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_pkey PRIMARY KEY (id);


--
-- Name: team_members team_members_team_id_player_profile_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_team_id_player_profile_id_key UNIQUE (team_id, player_profile_id);


--
-- Name: teams teams_name_region_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_name_region_id_key UNIQUE (name, region_id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- Name: teams teams_tag_region_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_tag_region_id_key UNIQUE (tag, region_id);


--
-- Name: tournament_matches tournament_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_matches
    ADD CONSTRAINT tournament_matches_pkey PRIMARY KEY (id);


--
-- Name: tournament_registrations tournament_registrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_registrations
    ADD CONSTRAINT tournament_registrations_pkey PRIMARY KEY (id);


--
-- Name: tournament_registrations tournament_registrations_tournament_id_participant_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournament_registrations
    ADD CONSTRAINT tournament_registrations_tournament_id_participant_id_key UNIQUE (tournament_id, participant_id);


--
-- Name: tournaments tournaments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournaments
    ADD CONSTRAINT tournaments_pkey PRIMARY KEY (id);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (id);


--
-- Name: user_roles user_roles_user_id_role_id_region_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_role_id_region_id_key UNIQUE (user_id, role_id, region_id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: ix_matches_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_matches_id ON public.matches USING btree (id);


--
-- Name: ix_matches_season_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_matches_season_id ON public.matches USING btree (season_id);


--
-- Name: ix_matches_team_a_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_matches_team_a_id ON public.matches USING btree (team_a_id);


--
-- Name: ix_matches_team_b_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_matches_team_b_id ON public.matches USING btree (team_b_id);


--
-- Name: ix_matches_tournament_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_matches_tournament_id ON public.matches USING btree (tournament_id);


--
-- Name: ix_player_profiles_contract_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_contract_status ON public.player_profiles USING btree (contract_status);


--
-- Name: ix_player_profiles_current_rating; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_current_rating ON public.player_profiles USING btree (current_rating);


--
-- Name: ix_player_profiles_current_team_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_current_team_id ON public.player_profiles USING btree (current_team_id);


--
-- Name: ix_player_profiles_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_id ON public.player_profiles USING btree (id);


--
-- Name: ix_player_profiles_player_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_player_name ON public.player_profiles USING btree (player_name);


--
-- Name: ix_player_profiles_position; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_position ON public.player_profiles USING btree ("position");


--
-- Name: ix_player_profiles_profile_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_player_profiles_profile_id ON public.player_profiles USING btree (profile_id);


--
-- Name: ix_player_profiles_region_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_region_id ON public.player_profiles USING btree (region_id);


--
-- Name: ix_player_profiles_summoner_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_summoner_name ON public.player_profiles USING btree (summoner_name);


--
-- Name: ix_player_profiles_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_player_profiles_user_id ON public.player_profiles USING btree (user_id);


--
-- Name: ix_regions_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_regions_id ON public.regions USING btree (id);


--
-- Name: ix_regions_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_regions_name ON public.regions USING btree (name);


--
-- Name: ix_seasons_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seasons_id ON public.seasons USING btree (id);


--
-- Name: ix_seasons_region_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_seasons_region_id ON public.seasons USING btree (region_id);


--
-- Name: ix_team_members_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_team_members_id ON public.team_members USING btree (id);


--
-- Name: ix_team_members_player_profile_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_team_members_player_profile_id ON public.team_members USING btree (player_profile_id);


--
-- Name: ix_team_members_team_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_team_members_team_id ON public.team_members USING btree (team_id);


--
-- Name: ix_teams_captain_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teams_captain_user_id ON public.teams USING btree (captain_user_id);


--
-- Name: ix_teams_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teams_id ON public.teams USING btree (id);


--
-- Name: ix_teams_region_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_teams_region_id ON public.teams USING btree (region_id);


--
-- Name: ix_tournaments_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournaments_created_by ON public.tournaments USING btree (created_by);


--
-- Name: ix_tournaments_region_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournaments_region_id ON public.tournaments USING btree (region_id);


--
-- Name: ix_tournaments_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tournaments_status ON public.tournaments USING btree (status);


--
-- Name: ix_users_riot_summoner_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_riot_summoner_name ON public.users USING btree (riot_summoner_name);


--
-- Name: matches matches_season_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_season_id_fkey FOREIGN KEY (season_id) REFERENCES public.seasons(id) ON DELETE CASCADE;


--
-- Name: matches matches_team_a_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_team_a_id_fkey FOREIGN KEY (team_a_id) REFERENCES public.teams(id);


--
-- Name: matches matches_team_b_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_team_b_id_fkey FOREIGN KEY (team_b_id) REFERENCES public.teams(id);


--
-- Name: matches matches_tournament_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_tournament_id_fkey FOREIGN KEY (tournament_id) REFERENCES public.tournaments(id) ON DELETE CASCADE;


--
-- Name: player_profiles player_profiles_current_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_profiles
    ADD CONSTRAINT player_profiles_current_team_id_fkey FOREIGN KEY (current_team_id) REFERENCES public.teams(id) ON DELETE SET NULL;


--
-- Name: player_profiles player_profiles_region_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_profiles
    ADD CONSTRAINT player_profiles_region_id_fkey FOREIGN KEY (region_id) REFERENCES public.regions(id) ON DELETE CASCADE;


--
-- Name: player_profiles player_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.player_profiles
    ADD CONSTRAINT player_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: regions regions_admin_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT regions_admin_user_id_fkey FOREIGN KEY (admin_user_id) REFERENCES public.users(id);


--
-- Name: role_permissions role_permissions_permission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey FOREIGN KEY (permission_id) REFERENCES public.permissions(id) ON DELETE CASCADE;


--
-- Name: role_permissions role_permissions_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: seasons seasons_region_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT seasons_region_id_fkey FOREIGN KEY (region_id) REFERENCES public.regions(id) ON DELETE CASCADE;


--
-- Name: team_members team_members_player_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_player_profile_id_fkey FOREIGN KEY (player_profile_id) REFERENCES public.player_profiles(id) ON DELETE CASCADE;


--
-- Name: team_members team_members_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE CASCADE;


--
-- Name: teams teams_captain_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_captain_user_id_fkey FOREIGN KEY (captain_user_id) REFERENCES public.users(id);


--
-- Name: teams teams_region_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_region_id_fkey FOREIGN KEY (region_id) REFERENCES public.regions(id) ON DELETE CASCADE;


--
-- Name: tournaments tournaments_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournaments
    ADD CONSTRAINT tournaments_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: tournaments tournaments_region_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tournaments
    ADD CONSTRAINT tournaments_region_id_fkey FOREIGN KEY (region_id) REFERENCES public.regions(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_granted_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_granted_by_user_id_fkey FOREIGN KEY (granted_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: user_roles user_roles_region_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_region_id_fkey FOREIGN KEY (region_id) REFERENCES public.regions(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict HNEivBQkdgixIN66acgu0u01enWqRGFBYTquQZ8p6V1k0qbrk0v5OhTHr7CfS0f

