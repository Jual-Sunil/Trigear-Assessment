import React, { useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  IconButton,
  Divider,
  Avatar,
  Tooltip,
  useMediaQuery,
  useTheme,
  CssBaseline,
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import EmailIcon from "@mui/icons-material/Email";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import WorkIcon from "@mui/icons-material/Work";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import SearchIcon from "@mui/icons-material/Search";
import MenuIcon from "@mui/icons-material/Menu";
import LogoutIcon from "@mui/icons-material/Logout";
import { useAuthStore } from "../store/authStore";
import { apiClient } from "../services/api/client";

const DRAWER_WIDTH = 220;

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", path: "/", icon: <DashboardIcon fontSize="small" /> },
  { label: "Emails", path: "/emails", icon: <EmailIcon fontSize="small" /> },
  { label: "Tasks", path: "/tasks", icon: <TaskAltIcon fontSize="small" /> },
  { label: "Jobs", path: "/jobs", icon: <WorkIcon fontSize="small" /> },
  { label: "Interviews", path: "/interviews", icon: <CalendarTodayIcon fontSize="small" /> },
  { label: "Search", path: "/search", icon: <SearchIcon fontSize="small" /> },
];

export function AppLayout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, clearAuth } = useAuthStore();
  const navigate = useNavigate();

  async function handleLogout() {
    await apiClient.post("/auth/logout");
    clearAuth();
    navigate("/login");
  }

  const drawerContent = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Toolbar sx={{ px: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }} noWrap>
          Mail Intel
        </Typography>
      </Toolbar>
      <Divider />
      <List dense sx={{ flex: 1, pt: 1 }}>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            component={NavLink}
            to={item.path}
            end={item.path === "/"}
            onClick={() => isMobile && setMobileOpen(false)}
            sx={{
              borderRadius: 1,
              mx: 1,
              mb: 0.5,
              "&.active": {
                bgcolor: "primary.main",
                color: "primary.contrastText",
                "& .MuiListItemIcon-root": { color: "primary.contrastText" },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
            <ListItemText
            primary={
                <Typography sx={{ fontWeight: 700 }}>
                {item.label}
                </Typography>
            }
            />
          </ListItemButton>
        ))}
      </List>
      <Divider />
      <Box sx={{ p: 1.5, display: "flex", alignItems: "center", gap: 1 }}>
        <Avatar sx={{ width: 30, height: 30, fontSize: 13 }}>
          {user?.name?.charAt(0)?.toUpperCase() ?? "U"}
        </Avatar>
        <Typography variant="body2" noWrap sx={{ flex: 1, fontSize: 13 }}>
          {user?.name ?? user?.email ?? "User"}
        </Typography>
        <Tooltip title="Logout">
          <IconButton size="small" onClick={handleLogout}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          display: { sm: "none" },
          zIndex: theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar>
          <IconButton color="inherit" edge="start" onClick={() => setMobileOpen(true)}>
            <MenuIcon />
          </IconButton>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, ml: 1 }}>
            Mail Intel
          </Typography>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", sm: "none" },
            "& .MuiDrawer-paper": { width: DRAWER_WIDTH },
          }}
        >
          {drawerContent}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", sm: "block" },
            "& .MuiDrawer-paper": { width: DRAWER_WIDTH, boxSizing: "border-box" },
          }}
          open
        >
          {drawerContent}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          pt: { xs: 8, sm: 3 },
          px: 3,
          pb: 3,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}