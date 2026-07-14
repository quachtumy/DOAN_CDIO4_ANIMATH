import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm';

const supabaseUrl = 'https://rpsqcfxmepkskhakbjlj.supabase.co';
const supabaseKey = 'sb_publishable_-8PERyEJauC-2xaFHrjsRg_fDwWkYDC';

export const supabase = createClient(supabaseUrl, supabaseKey);
