import { Sidebar } from "../sidebar/Sidebar";
import { MainView } from "../main_view/MainView";
import { AiView } from "../ai_panel/AiView";

export function DashboardShell(){
    return(
        <div className="grid grid-cols-[auto_1fr_auto] h-screen">
            <Sidebar/>
            <MainView/>
            <AiView/>
        </div>
    )
}