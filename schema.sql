-- Student Marketplace Supabase schema
-- Run this once in Supabase SQL Editor.

create extension if not exists pgcrypto;

create table if not exists profiles (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text unique not null,
  password_hash text not null,
  course text not null,
  year text not null,
  is_verified boolean default true,
  is_admin boolean default false,
  created_at timestamptz default now()
);

create table if not exists listings (
  id uuid primary key default gen_random_uuid(),
  seller_id uuid references profiles(id) on delete cascade,
  title text not null,
  description text,
  category text not null check (category in ('Textbooks','Calculators','Notes','Stationery','Lab coats','Other')),
  price numeric not null check (price >= 0),
  condition text not null check (condition in ('New','Like New','Good','Fair','Used')),
  course text,
  year text,
  status text not null default 'available' check (status in ('available','reserved','sold')),
  image_url text,
  created_at timestamptz default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  listing_id uuid references listings(id) on delete cascade,
  sender_id uuid references profiles(id) on delete cascade,
  receiver_id uuid references profiles(id) on delete cascade,
  body text not null,
  created_at timestamptz default now()
);

create table if not exists notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references profiles(id) on delete cascade,
  title text not null,
  body text not null,
  is_read boolean default false,
  created_at timestamptz default now()
);

-- Optional storage bucket for listing images. Create this from Supabase Dashboard > Storage if SQL fails:
-- Bucket name: listing-images, Public bucket: ON
insert into storage.buckets (id, name, public)
values ('listing-images', 'listing-images', true)
on conflict (id) do nothing;

-- Simple public policies for MVP. Tighten these before production.
alter table profiles enable row level security;
alter table listings enable row level security;
alter table messages enable row level security;
alter table notifications enable row level security;

create policy "mvp_profiles_all" on profiles for all using (true) with check (true);
create policy "mvp_listings_all" on listings for all using (true) with check (true);
create policy "mvp_messages_all" on messages for all using (true) with check (true);
create policy "mvp_notifications_all" on notifications for all using (true) with check (true);

create policy "mvp_storage_read" on storage.objects for select using (bucket_id = 'listing-images');
create policy "mvp_storage_insert" on storage.objects for insert with check (bucket_id = 'listing-images');
