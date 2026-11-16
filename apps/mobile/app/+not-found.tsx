import {View,Text,StyleSheet} from 'react-native';
import {Link} from 'expo-router';
export default function NotFound(){return <View style={styles.root}><Text style={styles.title}>Sahifa topilmadi</Text><Link href="/" style={styles.link}>Bosh sahifaga qaytish</Link></View>;}
const styles=StyleSheet.create({root:{flex:1,backgroundColor:'#090d14',alignItems:'center',justifyContent:'center',gap:20},title:{fontSize:24,color:'#e9edf5'},link:{color:'#8fb6ff'}});
