-- Add super_admin flag to profiles
-- Only Grid Control owner (Gaurav) gets this. Clients never see admin pages.
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_super_admin boolean DEFAULT false;

-- Set Gaurav as super admin by email
UPDATE profiles SET is_super_admin = true WHERE email = 'offgridcreativesai@gmail.com';

-- RLS policy: super admins can read all brands
CREATE POLICY "super_admin_read_all_brands" ON brands
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND is_super_admin = true
    )
  );

-- Super admins can read all brand_members
CREATE POLICY "super_admin_read_all_members" ON brand_members
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profiles WHERE id = auth.uid() AND is_super_admin = true
    )
  );
