import { Header } from "./Header";
import { Sidebar } from "../sidebar/Sidebar";
import { MainView } from "../main_view/MainView";
import { AiView } from "../ai_panel/AiView";

export function DashboardShell(){
    return(
        <div className="flex h-screen flex-col bg-background text-foreground">
            <Header/>
            <div className="grid flex-1 grid-cols-[auto_1fr_auto] overflow-hidden">
                <Sidebar/>
                <MainView/>
                <AiView/>
            </div>
        </div>
    )
}
