-- Complete FlyEsports Database Schema

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    riot_summoner_name VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_riot_summoner_name ON users(riot_summoner_name);

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    level INTEGER NOT NULL DEFAULT 0,
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_roles_id ON roles(id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_roles_name ON roles(name);

-- Regions table
CREATE TABLE IF NOT EXISTS regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    admin_user_id INTEGER NOT NULL REFERENCES users(id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    max_teams_per_season INTEGER NOT NULL DEFAULT 16,
    allow_public_registration BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_regions_id ON regions(id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_regions_name ON regions(name);

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    UNIQUE(resource, action)
);

CREATE INDEX IF NOT EXISTS ix_permissions_id ON permissions(id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_permissions_name ON permissions(name);
CREATE INDEX IF NOT EXISTS ix_permissions_resource ON permissions(resource);

-- Role permissions table
CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    UNIQUE(role_id, permission_id)
);

-- User roles table
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    region_id INTEGER REFERENCES regions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    granted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    UNIQUE(user_id, role_id, region_id)
);

CREATE INDEX IF NOT EXISTS ix_user_roles_id ON user_roles(id);

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    tag VARCHAR(10) NOT NULL,
    description TEXT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    captain_user_id INTEGER NOT NULL REFERENCES users(id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_recruiting BOOLEAN NOT NULL DEFAULT false,
    min_rank_requirement VARCHAR(20),
    max_members INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    UNIQUE(name, region_id),
    UNIQUE(tag, region_id)
);

CREATE INDEX IF NOT EXISTS ix_teams_id ON teams(id);
CREATE INDEX IF NOT EXISTS ix_teams_region_id ON teams(region_id);
CREATE INDEX IF NOT EXISTS ix_teams_captain_user_id ON teams(captain_user_id);

-- Player profiles table
CREATE TABLE IF NOT EXISTS player_profiles (
    id SERIAL PRIMARY KEY,
    profile_id VARCHAR(50) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    player_name VARCHAR(100) NOT NULL,
    summoner_name VARCHAR(100) NOT NULL,
    position VARCHAR(20) NOT NULL DEFAULT 'FILL',
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    current_team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    current_rating FLOAT NOT NULL DEFAULT 1200.0,
    peak_rating FLOAT NOT NULL DEFAULT 1200.0,
    rank_tier VARCHAR(20),
    rank_division VARCHAR(10),
    league_points INTEGER DEFAULT 0,
    contract_status VARCHAR(20) NOT NULL DEFAULT 'FREE_AGENT',
    total_matches INTEGER NOT NULL DEFAULT 0,
    total_wins INTEGER NOT NULL DEFAULT 0,
    total_losses INTEGER NOT NULL DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_player_profiles_id ON player_profiles(id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_player_profiles_profile_id ON player_profiles(profile_id);
CREATE INDEX IF NOT EXISTS ix_player_profiles_user_id ON player_profiles(user_id);
CREATE INDEX IF NOT EXISTS ix_player_profiles_region_id ON player_profiles(region_id);
CREATE INDEX IF NOT EXISTS ix_player_profiles_current_team_id ON player_profiles(current_team_id);

-- Tournaments table
CREATE TABLE IF NOT EXISTS tournaments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    tournament_type VARCHAR(20) NOT NULL DEFAULT 'TEAM',
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    created_by_user_id INTEGER NOT NULL REFERENCES users(id),
    registration_start TIMESTAMP WITH TIME ZONE NOT NULL,
    registration_end TIMESTAMP WITH TIME ZONE NOT NULL,
    tournament_start TIMESTAMP WITH TIME ZONE NOT NULL,
    tournament_end TIMESTAMP WITH TIME ZONE NOT NULL,
    format VARCHAR(20) NOT NULL DEFAULT 'SINGLE_ELIMINATION',
    max_participants INTEGER NOT NULL DEFAULT 16,
    team_size INTEGER DEFAULT 5,
    min_rank VARCHAR(20),
    max_rank VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    registration_count INTEGER NOT NULL DEFAULT 0,
    logo_url VARCHAR(500),
    banner_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_tournaments_region_id ON tournaments(region_id);
CREATE INDEX IF NOT EXISTS ix_tournaments_created_by_user_id ON tournaments(created_by_user_id);
CREATE INDEX IF NOT EXISTS ix_tournaments_status ON tournaments(status);

-- Seasons table
CREATE TABLE IF NOT EXISTS seasons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    region_id INTEGER NOT NULL REFERENCES regions(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'UPCOMING',
    max_teams INTEGER NOT NULL DEFAULT 16,
    registration_deadline DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    UNIQUE(name, region_id)
);

CREATE INDEX IF NOT EXISTS ix_seasons_id ON seasons(id);
CREATE INDEX IF NOT EXISTS ix_seasons_region_id ON seasons(region_id);

-- Matches table
CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    tournament_id UUID REFERENCES tournaments(id) ON DELETE CASCADE,
    season_id INTEGER REFERENCES seasons(id) ON DELETE CASCADE,
    team_a_id INTEGER NOT NULL REFERENCES teams(id),
    team_b_id INTEGER NOT NULL REFERENCES teams(id),
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
    result VARCHAR(20),
    team_a_score INTEGER DEFAULT 0,
    team_b_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_matches_id ON matches(id);
CREATE INDEX IF NOT EXISTS ix_matches_tournament_id ON matches(tournament_id);
CREATE INDEX IF NOT EXISTS ix_matches_season_id ON matches(season_id);
CREATE INDEX IF NOT EXISTS ix_matches_team_a_id ON matches(team_a_id);
CREATE INDEX IF NOT EXISTS ix_matches_team_b_id ON matches(team_b_id);

-- Team members table
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    player_profile_id INTEGER NOT NULL REFERENCES player_profiles(id) ON DELETE CASCADE,
    position VARCHAR(20) NOT NULL DEFAULT 'FILL',
    is_captain BOOLEAN NOT NULL DEFAULT false,
    is_substitute BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    left_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    UNIQUE(team_id, player_profile_id)
);

CREATE INDEX IF NOT EXISTS ix_team_members_id ON team_members(id);
CREATE INDEX IF NOT EXISTS ix_team_members_team_id ON team_members(team_id);
CREATE INDEX IF NOT EXISTS ix_team_members_player_profile_id ON team_members(player_profile_id);

-- Alembic version table
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) VALUES ('fcd6ab261e40')
ON CONFLICT (version_num) DO NOTHING;